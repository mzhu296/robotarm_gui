import asyncio
import logging
import time
from nicegui import app, ui
from udpclient import UDPClient
from controls import controls
from ai_controller import process_ai_command, voice_command  # 🗣️ Import voice control

logging.getLogger('nicegui').setLevel(logging.ERROR)
ui.colors(primary='#6e93d6')

devices = {}

ui.markdown('### Rboot GUI')
ui.markdown('Waiting for Rboot CAN2ETH Gateway devices to be connected...').bind_visibility_from(globals(), 'devices', lambda d: not d)
container = ui.row()

async def discovery_loop():
    client = UDPClient('192.168.8.88', 9999)
    if await asyncio.to_thread(client.is_server_up):  
        client.connect()
        client.start_receive_thread()

        devices[id(client)] = ui.column()
        with devices[id(client)]:
            controls(client)

            # AI Command Input UI
            command_box = ui.textarea('Enter AI Command')
            ui.button('Send to AI', on_click=lambda: ui.notify(process_ai_command(client, command_box.value)))

            # 🗣️ Voice Command Button
            ui.button("🎤 Speak Command", on_click=lambda: ui.notify(voice_command(client)))

    else:
        print("Not connected to the server.")

app.on_startup(discovery_loop)

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Rboot GUI")


# import asyncio
# import logging
# import time
# from nicegui import app, ui
# from udpclient import UDPClient
# from controls import controls
# from ai_controller import process_ai_command  # Import AI module

# logging.getLogger('nicegui').setLevel(logging.ERROR)
# ui.colors(primary='#6e93d6')

# devices = {}

# ui.markdown('### Rboot GUI')
# ui.markdown('Waiting for Rboot CAN2ETH Gateway devices to be connected...').bind_visibility_from(globals(), 'devices', lambda d: not d)
# container = ui.row()

# async def discovery_loop():
#     client = UDPClient('192.168.8.88', 9999)
#     if await asyncio.to_thread(client.is_server_up):  
#         client.connect()
#         client.start_receive_thread()

#         devices[id(client)] = ui.column()
#         with devices[id(client)]:
#             controls(client)

#             # AI Command Input UI
#             command_box = ui.textarea('Enter AI Command')
#             ui.button('Send to AI', on_click=lambda: ui.notify(process_ai_command(client, command_box.value)))

#     else:
#         print("Not connected to the server.")

# app.on_startup(discovery_loop)

# if __name__ in {"__main__", "__mp_main__"}:
#     ui.run(title="Rboot GUI")
