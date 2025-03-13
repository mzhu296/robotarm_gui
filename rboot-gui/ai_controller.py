# import openai
# import can_data
# import struct
# import re
# import speech_recognition as sr  # 🗣️ Add speech recognition

# # Set up the DeepSeek AI client with LM Studio
# client = openai.OpenAI(
#     api_key="EMPTY",  # No API key needed for LM Studio
#     base_url="http://localhost:1234/v1"  # Ensure LM Studio is running
# )

# # Function to generate a response from AI
# def generate_response(prompt):
#     response = client.chat.completions.create(
#         model="deepseek-r1",
#         messages=[
#             {"role": "system", "content": "You are a robotic control AI assistant. "
#              "Always respond with six numerical joint values, separated by commas, including negative values where appropriate. "
#              "Example: '-14, 25, -45, 0, 3, -25'."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0.7,
#         max_tokens=200
#     )
#     return response.choices[0].message.content

# import re

# def process_ai_command(udp_client, command_text):
#     ai_response = generate_response(command_text)
#     print(f"🔹 AI Response: {ai_response}")  # Debugging output

#     # ✅ Use regex to extract negative & positive numbers
#     joint_values = re.findall(r'-?\d+\.\d+|-?\d+', ai_response)  
#     joint_values = [float(x) for x in joint_values][:6]  # ✅ Ensure exactly 6 values

#     print(f"🔹 Extracted joint values: {joint_values}")  # Debugging output

#     if len(joint_values) == 6:
#         send_joint_positions(udp_client, joint_values)
#         return f"✅ Sent command to move joints: {joint_values}"
#     else:
#         return f"⚠️ Error: AI response did not contain 6 valid joint positions. Extracted: {joint_values}"
    
# # Function to send joint positions via UDP
# def send_joint_positions(udp_client, joint_angles):
#     for i, angle in enumerate(joint_angles):
#         cid = i + 1  # Motor ID (J1 = 1, J2 = 2, ...)
#         reduction_value = 50  # Adjust based on your robot's motor settings
#         motor_cnt = angle / 360.0 * reduction_value
#         pos = struct.pack('<f', float(motor_cnt))
#         cmd2 = struct.pack('<HH', 60, 10)

#         udp_client.send_message(
#             cid,
#             can_data.command_id['Set_Input_Pos'],
#             pos,
#             cmd2,
#             can_data.Message_type['short']
#         )
import openai
import can_data
import struct
import re
import time
import speech_recognition as sr 

# Set up DeepSeek AI client
client = openai.OpenAI(
    api_key="EMPTY",
    base_url="http://localhost:1234/v1"
)

# Predefined positions for special commands
PRESET_MOVEMENTS = {
    "home": [0, 0, 0, 0, 0, 0],  # Home position (All joints at 0°)
    "wave_hello": [
        [0, 45, 0, 90, 0, 0],  # Raise arm
        [0, 45, 0, -90, 0, 0],  # Move left
        [0, 45, 0, 90, 0, 0],  # Move right
        [0, 45, 0, -90, 0, 0],  # Move left
        [0, 0, 0, 0, 0, 0]  # Return to rest position
    ]
}

# Function to generate AI response
def generate_response(prompt):
    response = client.chat.completions.create(
        model="deepseek-r1",
        messages=[
            {"role": "system", "content": "You are a robotic control AI assistant. "
             "Always respond with six numerical joint values, separated by commas, including negative values where appropriate. "
             "Example: '-30, 45, 60, -20, 10, -5'. "
             "Recognize and respond correctly to high-level commands like 'Move to home position', 'Wave hello', or 'Stop movement'."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=200
    )
    return response.choices[0].message.content

# Function to process AI-generated commands
def process_ai_command(udp_client, command_text):
    command_text = command_text.lower().strip()  # Normalize input
    print(f"🔹 Received Command: {command_text}")

    # Handle special commands
    if "home" in command_text or "reset" in command_text:
        print("Moving to Home Position...")
        send_joint_positions(udp_client, PRESET_MOVEMENTS["home"])
        return "Robot moved to home position."

    elif "wave" in command_text:
        print("Performing Wave Hello...")
        for pose in PRESET_MOVEMENTS["wave_hello"]:
            send_joint_positions(udp_client, pose)
            time.sleep(1)  # Delay between movements
        return "Robot completed waving motion."

    elif "stop" in command_text or "halt" in command_text:
        print("Stopping all movement...")
        send_idle_mode(udp_client)  # Send IDLE mode command
        return "Robot stopped."

    # Extract numerical values for normal movement
    ai_response = generate_response(command_text)
    print(f"🔹 AI Response: {ai_response}")

    joint_values = re.findall(r'-?\d+\.\d+|-?\d+', ai_response)  
    joint_values = [float(x) for x in joint_values][:6]  

    print(f"🔹 Extracted joint values: {joint_values}")

    if len(joint_values) == 6:
        send_joint_positions(udp_client, joint_values)
        return f"Sent command to move joints: {joint_values}"
    else:
        return f"Error: AI response did not contain 6 valid joint positions. Extracted: {joint_values}"

# Function to send joint positions via UDP
def send_joint_positions(udp_client, joint_angles):
    for i, angle in enumerate(joint_angles):
        cid = i + 1  # Motor ID
        reduction_value = 50  
        motor_cnt = angle / 360.0 * reduction_value
        pos = struct.pack('<f', float(motor_cnt))
        cmd2 = struct.pack('<HH', 60, 10)

        udp_client.send_message(
            cid,
            can_data.command_id['Set_Input_Pos'],
            pos,
            cmd2,
            can_data.Message_type['short']
        )

# Function to set all motors to IDLE mode (stop movement)
def send_idle_mode(udp_client):
    for i in range(1, 7):
        udp_client.send_message(
            i,
            can_data.command_id['Set_Axis_State'],
            struct.pack('<I', can_data.AxisState['IDLE']),
            struct.pack('<I', 0),
            can_data.Message_type['short']
        )

# 🗣️ Voice Control Function
def voice_command(udp_client):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for voice command...")
        try:
            recognizer.adjust_for_ambient_noise(source)  # Adjust for background noise
            audio = recognizer.listen(source)  # Capture audio

            # Convert speech to text
            command_text = recognizer.recognize_google(audio)
            print(f"Recognized: {command_text}")  # Debugging output

            return process_ai_command(udp_client, command_text)

        except sr.UnknownValueError:
            return "Could not understand the voice command."
        except sr.RequestError:
            return "Speech Recognition service unavailable."


# import openai
# import can_data
# import struct


# # Set up the DeepSeek client with LM Studio
# client = openai.OpenAI(
#     api_key="EMPTY",  # No API key needed for LM Studio
#     base_url="http://localhost:1234/v1"  # Ensure LM Studio is running here
# )

# # Function to send a text command to DeepSeek and return a response
# def generate_response(prompt):
#     response = client.chat.completions.create(
#         model="deepseek-r1",
#         messages=[
#             {"role": "system", "content": "You are a robotic control AI assistant. "
#              "Always respond with six numerical joint values, separated by commas, including negative values where appropriate. "
#              "Example format: 'J1: -30, J2: 45, J3: 60, J4: -20, J5: 10, J6: -5'."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0.7,
#         max_tokens=200
#     )
#     return response.choices[0].message.content

# # Function to interpret AI commands and send movement instructions
# import re

# def process_ai_command(udp_client, command_text):
#     ai_response = generate_response(command_text)
#     print(f"🔹 AI Response: {ai_response}")  # Debugging output

#     # ✅ Improved regex to extract negative and positive numbers
#     joint_values = re.findall(r'-?\d+\.\d+|-?\d+', ai_response)  # Captures negative numbers

#     # ✅ Convert to float and ensure exactly 6 values
#     joint_values = [float(x) for x in joint_values][:6]
#     print(f"🔹 Extracted joint values: {joint_values}")  # Debugging output

#     if len(joint_values) == 6:
#         send_joint_positions(udp_client, joint_values)
#         return f"✅ Sent command to move joints: {joint_values}"
#     else:
#         return f"⚠️ Error: AI response did not contain 6 valid joint positions. Extracted: {joint_values}"


# # Function to send joint positions via UDP
# def send_joint_positions(udp_client, joint_angles):
#     for i, angle in enumerate(joint_angles):
#         cid = i + 1  # Motor ID (J1 = 1, J2 = 2, ...)
#         position = angle
#         reduction_value = 50  # Adjust based on your robot's motor settings
#         motor_cnt = position / 360.0 * reduction_value
#         pos = struct.pack('<f', float(motor_cnt))
#         cmd2 = struct.pack('<HH', 60, 10)

#         udp_client.send_message(
#             cid,
#             can_data.command_id['Set_Input_Pos'],
#             pos,
#             cmd2,
#             can_data.Message_type['short']
#         )
