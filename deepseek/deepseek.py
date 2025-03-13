import openai

# Set API key and base URL for LM Studio
client = openai.OpenAI(
    api_key="EMPTY",  # LM Studio does not require an actual API key
    base_url="http://localhost:1234/v1"  # Ensure this matches LM Studio's server address
)

# Function to generate a response
def generate_response(prompt):
    response = client.chat.completions.create(
        model="deepseek-r1",  # Ensure this matches the model name in LM Studio
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=200
    )
    return response.choices[0].message.content

# Example usage
prompt = "hello"
response = generate_response(prompt)
print(response)
