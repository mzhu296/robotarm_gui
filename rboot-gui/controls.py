from datetime import datetime
from typing import Any

from nicegui import ui
from odrive.pyfibre import fibre
from odrive.utils import dump_errors
import can_data
import struct
import time
import json
import threading
# from local_file_picker import local_file_picker

default = {'motor': 0}
motors_cfg = {'M1': 
                {'position': 0.0, 
                'velocity': 0.0,
                'status': 0,
                'error': 0,
                'iq': 0.0,
                'voltage': 0.0,
                'ibus': 0.0,
                'reduction': 50,
                'teaching': 0,
                'ccw': 0,
                },
                'M2':
                {'position': 0.0,
                'velocity': 0.0,                   
                'status': 0,
                'error': 0,
                'iq': 0.0,
                'voltage': 0.0,
                'ibus': 0.0,
                'reduction': 50,
                'teaching': 0,
                'ccw': 0,
                },
                'M3':
                {'position': 0.0,
                'velocity': 0.0,
                'status': 0,
                'error': 0,
                'iq': 0.0,
                'voltage': 0.0,
                'ibus': 0.0,
                'reduction': 50,
                'teaching': 0,
                'ccw': 0,
                },
                'M4':
                {'position': 0.0,
                'velocity': 0.0,
                'status': 0,
                'error': 0,
                'iq': 0.0,
                'voltage': 0.0,
                'ibus': 0.0,
                'reduction': 30,
                'teaching': 0,
                'ccw': 0,
                },
                'M5':
                {'position': 0.0,
                'velocity': 0.0,
                'status': 0,
                'error': 0,
                'iq': 0.0,
                'voltage': 0.0,
                'ibus': 0.0,
                'reduction': 50,
                'teaching': 0,
                'ccw': 0,
                },
                'M6':
                {'position': 0.0,
                'velocity': 0.0,
                'status': 0,
                'error': 0,
                'iq': 0.0,
                'voltage': 0.0,
                'ibus': 0.0,
                'reduction': 50,
                'teaching': 0,
                'ccw': 0,
                },
                }

MODES = {
    0: 'Status',
    1: 'Controls',
    2: 'Teaching',
}

joint_angle_tmp = {'J1': 0.0, 'J2': 0.0, 'J3': 0.0, 'J4': 0.0, 'J5': 0.0, 'J6': 0.0, 'Delay': 1.5, 'Gripper': 0, 'Torque': 0.0}
joint_angle_lock = threading.Lock()
joint_json = 'jason.json'

teaching = []    
count = 0    

buffer = []

last_print_time = time.time()

def print_buffer():
    global last_print_time, buffer
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    for data in buffer:
        print(f"{data[0]}: Position: {data[1]}")
    buffer.clear()
    last_print_time = time.time()

def check_and_print_buffer():
    global last_print_time
    if time.time() - last_print_time >= 10:
        print_buffer()
        
def controls(client) -> None:
    def get_reduction(i):
        motor_keys = list(motors_cfg.keys()) 
        motor_name = motor_keys[i]
        return motors_cfg[motor_name]['reduction']
         
    def send_msg(id, type, cmd1, cmd2) -> None:
         client.send_message(id, type, struct.pack('<I', cmd1), struct.pack('<I', cmd2), can_data.Message_type['short'])

    def send_6d_msg(id, type, cmd1, cmd2) -> None:
        for i in range(6):
            cid = i + 1
            client.send_message(cid, type, struct.pack('<I', cmd1), struct.pack('<I', cmd2), can_data.Message_type['short'])

    def send_position(id, sign: int, position) -> None:
        # print("send_position.....", id)
        cid = int(id)
        reduction_value = get_reduction(cid - 1)
        motorCnt = position / 360.0 * reduction_value
        pos = struct.pack('<f', sign * float(motorCnt))
        cmd2 = struct.pack('<HH', 60, 10)
        print(cid, sign, position, pos, cmd2)
        client.send_message(cid, can_data.command_id['Set_Input_Pos'], pos, cmd2, can_data.Message_type['short'])

    def send_torque(id, sign: int, position) -> None:
        print("torque.....", sign, sign * float(position))
        cid = int(7)
        pos = struct.pack('<f', sign * float(position))
        vel = struct.pack('<f', 1)
        client.send_message(cid, can_data.command_id['Set_Controller_Mode'], struct.pack('<I', can_data.ControlMode['TORQUE_CONTROL']), struct.pack('<I', can_data.InputMode['PASSTHROUGH']), can_data.Message_type['short'])
        send_msg(cid, can_data.command_id['Set_Axis_State'], can_data.AxisState['CLOSED_LOOP_CONTROL'], can_data.Message_type['short'])
        client.send_message(cid, can_data.command_id['Set_Input_Vel'], vel, pos, can_data.Message_type['short'])

    def set_abs_pos(id, sign: int, position) -> None:
        # print("torque.....")
        cid = int(7)
        pos = struct.pack('<f', sign * float(position))
        vel = struct.pack('<f', 30)
        client.send_message(cid, can_data.command_id['Set_Controller_Mode'], struct.pack('<I', can_data.ControlMode['TORQUE_CONTROL']), struct.pack('<I', can_data.InputMode['PASSTHROUGH']), can_data.Message_type['short'])
        send_msg(cid, can_data.command_id['Set_Axis_State'], can_data.AxisState['CLOSED_LOOP_CONTROL'], can_data.Message_type['short'])
        client.send_message(cid, can_data.command_id['Set_Input_Vel'], vel, pos, can_data.Message_type['short'])

    def send_6d_position(sign: int, position) -> None:
        for i, a in enumerate(position):
            cid = i + 1
            # if i == 3
            reduction_value = get_reduction(i)
            motorCnt = a / 360.0 * reduction_value
            pos = struct.pack('<f', sign * float(motorCnt))
            cmd2 = struct.pack('<HH', 0x1f, 0)
            client.send_message(cid, can_data.command_id['Set_Input_Pos'], pos, cmd2, can_data.Message_type['short'])
            #give an break to make sure udp package sent out success
            time.sleep(0.01)

    def udp_callback(data):
         update(data)
    
    def register_cb():
        client.register_callback(udp_callback) 
        send_msg(1, can_data.command_id['Set_Axis_State'], can_data.AxisState['IDLE'], can_data.Message_type['short'])        

    def unregister_cb():
        client.unregister_callback() 
        info_status.set_text(f'CAN BUS: Not enabled')
        info_status.style('color: #fc0320; font-weight: bold')

    # with ui.row().classes('w-full justify-between items-center'):
    #     with ui.row():
    #         ui.button('Start', on_click=register_cb)
    
    with ui.row().classes('w-full justify-between items-center'):
        with ui.row():
            # info_status = ui.label(f'CAN BUS:')
            with ui.chat_message():
                info_status = ui.label('CAN BUS:').props()
            # info_status = ui.chat_message('Can Bus:',
            #                 # name='Status',
            #                 stamp='now',
            #                 avatar='https://robohash.org/ui')
            
        with ui.row():
            ui.button(on_click=register_cb).props('icon=radio_button_checked round') \
                                    .tooltip('Connect to CAN BUS')
            ui.button(on_click=unregister_cb).props('icon=cancel round') \
                                    .tooltip('Disconnect to CAN BUS')
            ui.button(on_click=lambda: send_6d_msg(0, can_data.command_id['Set_Axis_State'], can_data.AxisState['CLOSED_LOOP_CONTROL'], 0)) \
                .props('icon=repeat round') \
                .tooltip('Enable all joints to close loop mode')
            ui.button(on_click=lambda: send_6d_msg(0, can_data.command_id['Set_Axis_State'], can_data.AxisState['IDLE'], 0)).props('icon=close round') \
                .tooltip('Enable all joints to idle mode')

        # with ui.row():
        #     ui.button(on_click=lambda: client.send_message("enable")) \
        #         .props('icon=restart_alt flat round') \
        #         .tooltip('enable monitor of can bus')

    # let's set toggled motor
    with ui.row():
        mode = ui.toggle(MODES).bind_value(default, 'motor')

    with ui.row():
        count = 0
        # forw_data = [0, 0.0]
        for k,v in motors_cfg.items():
            count += 1
            # forw_data[0] += 1
            with ui.card().bind_visibility_from(mode, 'value', value=0):
                ui.markdown(f'##### {k}')
                with ui.column():
                    with ui.row():
                            ui.label('Status:')
                            ui.label('Status').bind_text_from(v, 'status')
                            ui.label('Error:')
                            ui.label('Error').bind_text_from(v, 'error')
                            ui.label('V:')
                            ui.label('V').bind_text_from(v, 'voltage')
                            # ui.label('Iq:')
                            # ui.label('Iq').bind_text_from(v, 'iq')
                            # ui.label('T:')
                            # ui.label('T').bind_text_from(v, 'ibus')
                    with ui.row():
                            ui.number('position', format='%.3f').bind_value(v, 'position').set_enabled(False)
                            ui.number('velocity', format='%.3f').bind_value(v, 'velocity').set_enabled(False)
                    with ui.row():
                            ui.number('Iq', format='%.3f').bind_value(v, 'iq').set_enabled(False)
                            ui.number('Ibus', format='%.3f').bind_value(v, 'ibus').set_enabled(False)
                    with ui.column():
                        with ui.row().classes('w-full'):
                                ui.button(on_click=lambda count=count: send_msg(count, can_data.command_id['Set_Axis_State'], can_data.AxisState['CLOSED_LOOP_CONTROL'], 0)) \
                                    .props('icon=repeat round') \
                                    .tooltip('Enable close loop mode')
                                ui.button(on_click=lambda count=count: send_msg(count, can_data.command_id['Set_Axis_State'], can_data.AxisState['IDLE'], 0)) \
                                    .props('icon=close round') \
                                    .tooltip('Enable idle mode')
                                ui.button(on_click=lambda count=count: send_msg(count, can_data.command_id['Set_Linear_Count'], 0, 0)) \
                                    .props('icon=adjust round') \
                                    .tooltip('Apply absolute zero position')
                                ui.button(on_click=lambda count=count: send_msg(count, can_data.command_id['Reboot'], can_data.Reboot['Reboot'], 0)) \
                                    .props('icon=restart_alt round') \
                                    .tooltip('Reboot motor')
                # m1_pos = ui.label().bind_text_from(v, 'id')
    # with ui.row():
    #     with ui.card().bind_visibility_from(mode, 'value', value=1):
    #         ui.markdown(f'##### Joint Control')
    #         with ui.row():
    #             with ui.column():
    #                 can_id = ui.number('Joint id', value=0)
    #             with ui.column():
    #                 position = ui.number('Input position', value=0)
    #                 def send_position_l(id, loc): send_position(id, loc, position.value)
    #         with ui.row():
    #                 ui.button(on_click=lambda: send_position_l(can_id.value, -1)).props('round flat icon=skip_previous')
    #                 ui.button(on_click=lambda: send_position_l(can_id.value, 0)).props('round flat icon=exposure_zero')
    #                 ui.button(on_click=lambda: send_position_l(can_id.value, 1)).props('round flat icon=skip_next')
            
    #     with ui.card().bind_visibility_from(mode, 'value', value=1):
    #         ui.markdown(f'##### Rboot Arm Control')
    #         with ui.row():
    #             with ui.column():
    #                 j1 = ui.number('J1', min=-175.00, max=175.00, value=0)
    #             with ui.column():
    #                 j2 = ui.number('J2', min=-115.00, max=75.00, value=0)
    #             with ui.column():
    #                 j3 = ui.number('J3', min=-60.00, max=90.00, value=0)
    #             with ui.column():
    #                 j4 = ui.number('J4', min=-180.00, max=180.00, value=0)
    #             with ui.column():
    #                 j5 = ui.number('J5', min=-110.00, max=120.00, value=0)
    #             with ui.column():
    #                 j6 = ui.number('J6', min=-180, max=180, value=0)
    #         with ui.row():
    #                 ui.button("Home", on_click=lambda: send_6d_position(0, [j1.value, j2.value, j3.value, j4.value, j5.value, j6.value])).props('round flat')
    #                 ui.button("Send", on_click=lambda: send_6d_position(1, [j1.value, j2.value, j3.value, j4.value, j5.value, j6.value])).props('round flat')

    # with ui.row():
    #     with ui.card().bind_visibility_from(mode, 'value', value=1):
    #         ui.markdown(f'##### Gripper Control')
    #         with ui.row():
    #             with ui.column():
    #                 gripper_id = ui.number('Gripper id', value=7)
    #             with ui.column():
    #                 torque = ui.number('Input torque', value=0)
    #                 def send_torque_l(id, loc): send_torque(id, loc, torque.value)
    #             # with ui.column():
    #             #     position = ui.number('Input position', value=0)
    #             #     def send_position_l(id, loc): send_position(id, loc, position.value)
    #         with ui.row():
    #                 ui.button(on_click=lambda: send_torque_l(gripper_id.value, -1)).props('round flat icon=skip_previous')
    #                 ui.button(on_click=lambda: send_torque_l(gripper_id.value, 0)).props('round flat icon=exposure_zero')
    #                 ui.button(on_click=lambda: send_torque_l(gripper_id.value, 1)).props('round flat icon=skip_next')
    with ui.row():
        with ui.card().bind_visibility_from(mode, 'value', value=1):
            ui.markdown('##### Joint Control')
            with ui.row():
                with ui.column():
                    ui.label('Joint id')
                    can_id = ui.slider(min=0, max=10, value=0, step=1)
                with ui.column():
                    ui.label('Input position')
                    position = ui.slider(min=-180, max=180, value=0)
                    def send_position_l(id, loc):
                        send_position(id, loc, position.value)
            with ui.row():
                ui.button(on_click=lambda: send_position_l(can_id.value, -1)).props('round flat icon=skip_previous')
                ui.button(on_click=lambda: send_position_l(can_id.value, 0)).props('round flat icon=exposure_zero')
                ui.button(on_click=lambda: send_position_l(can_id.value, 1)).props('round flat icon=skip_next')
                
        with ui.card().bind_visibility_from(mode, 'value', value=1).classes('w-full'):
            ui.markdown('##### Rboot Arm Control')

            # A row that can wrap if needed
            with ui.row().classes('flex-wrap w-full'):
                with ui.column().classes('w-1/6'):
                    ui.label('J1')
                    j1 = ui.slider(min=-175.00, max=175.00, value=0).classes('w-full')

                with ui.column().classes('w-1/6'):
                    ui.label('J2')
                    j2 = ui.slider(min=-115.00, max=75.00, value=0).classes('w-full')

                with ui.column().classes('w-1/6'):
                    ui.label('J3')
                    j3 = ui.slider(min=-60.00, max=90.00, value=0).classes('w-full')

                with ui.column().classes('w-1/6'):
                    ui.label('J4')
                    j4 = ui.slider(min=-180.00, max=180.00, value=0).classes('w-full')

                with ui.column().classes('w-1/6'):
                    ui.label('J5')
                    j5 = ui.slider(min=-110.00, max=120.00, value=0).classes('w-full')

                with ui.column().classes('w-1/6'):
                    ui.label('J6')
                    j6 = ui.slider(min=-180, max=180, value=0).classes('w-full')

            with ui.row():
                ui.button("Home", on_click=lambda: send_6d_position(
                    0, [j1.value, j2.value, j3.value, j4.value, j5.value, j6.value])
                ).props('round flat')
                ui.button("Send", on_click=lambda: send_6d_position(
                    1, [j1.value, j2.value, j3.value, j4.value, j5.value, j6.value])
                ).props('round flat')

        with ui.row():
            with ui.card().bind_visibility_from(mode, 'value', value=1):
                ui.markdown('##### Gripper Control')
                with ui.row():
                    with ui.column():
                        ui.label('Gripper id')
                        gripper_id = ui.slider(min=0, max=10, value=7, step=1)
                    with ui.column():
                        ui.label('Input torque')
                        torque = ui.slider(min=-100, max=100, value=0)
                        def send_torque_l(id, loc):
                            send_torque(id, loc, torque.value)
                with ui.row():
                    ui.button(on_click=lambda: send_torque_l(gripper_id.value, -1)).props('round flat icon=skip_previous')
                    ui.button(on_click=lambda: send_torque_l(gripper_id.value, 0)).props('round flat icon=exposure_zero')
                    ui.button(on_click=lambda: send_torque_l(gripper_id.value, 1)).props('round flat icon=skip_next')

    steps_container = ui.column()

    def add_angles():
        # joint_angles.append(joint_angle_tmp)
        with joint_angle_lock:
            new_joint_angle = joint_angle_tmp.copy()
            can_data.joint_angles.append(new_joint_angle)
        update_list()

    def remove_contact():
        with joint_angle_lock:
            can_data.joint_angles.pop()
        update_list()

    def send_steps_thread(d, r):
        for c in range(int(r)):
            for i, a in enumerate(can_data.joint_angles):
                send_6d_position(1, [a['J1'], a['J2'], a['J3'], a['J4'], a['J5'], a['J6']])
                if a['Gripper'] == 0:
                    send_torque(7, -1.0, a['Torque'])    
                    ui.notify(f'Gripper has been opened {a["Torque"]}')
                else:
                    send_torque(7, 1, a['Torque'])    
                ui.notify(f'Gripper has been closed {a["Torque"]}')            
                time.sleep(d)

    def repeat_steps(d, r):
        t = threading.Thread(target=send_steps_thread(d, r))
        t.start()

    async def pick_file() -> None:
        # result = await local_file_picker('~', multiple=False)
        # if result:
        #     joint_json = result[0]
        #     with open(joint_json, 'w') as file:
        #         json.dump(can_data.joint_angles, file, indent=4)
        #     ui.notify(f'You saved {joint_json}')
            update_list()

    async def open_file() -> None:
        # result = await local_file_picker('~', multiple=False)
        # if result:
        #     joint_json = result[0]
        #     with open(joint_json, 'r') as file:
        #         loaded_joint_angles = json.load(file)
        #         can_data.joint_angles = loaded_joint_angles
        #     ui.notify(f'You opened {joint_json}')
            update_list()

    def send_steps(i):
        ui.notify(f'Step {i} position has been sent out!!!')
        tmp_angle = can_data.joint_angles[i-1]
        send_6d_position(1, [tmp_angle['J1'], tmp_angle['J2'], tmp_angle['J3'], tmp_angle['J4'], tmp_angle['J5'], tmp_angle['J6']])
        if tmp_angle['Gripper'] == 0:
            send_torque(7, -1.0, tmp_angle['Torque'])    
            ui.notify(f'Gripper has been opened {tmp_angle["Torque"]}')
        else:
            send_torque(7, 1, tmp_angle['Torque'])    
            ui.notify(f'Gripper has been closed {tmp_angle["Torque"]}')            
    def update_list():
            steps_container.clear()
            with steps_container:
                with ui.card().bind_visibility_from(mode, 'value', value=2):
                    with ui.list().props('bordered separator'):
                        with ui.column():
                            with ui.row().classes('w-full'):
                                d = ui.number('Step delays(s)', format='%.3f', value=1.5) 
                                r = ui.number('Repeat times', format='%d', value=1) 
                                def send_delay_l(): repeat_steps(d.value, r.value)
                                ui.button('Add', on_click=add_angles)
                                ui.button('Delete', on_click=remove_contact)
                                ui.button('Repeat', on_click=send_delay_l)
                                ui.button('Save', on_click=pick_file)
                                ui.button('Open', on_click=open_file)
                            ui.separator()
                        with ui.column():
                            with ui.row().classes('w-full'):
                                for i, a in enumerate(can_data.joint_angles):
                                    item_select = ui.item(on_click=lambda i=i: send_steps(i + 1))
                                    item_select.default_classes('bg-blue-100 p-2')
                                    with item_select:
                                        with ui.item_section().props('avatar'):
                                            ui.icon('precision_manufacturing')
                                        with ui.item_section(f'Step {i+1}'):
                                            ui.number('Joint1', format='%.3f', value=a['J1'])                                      
                                            ui.number('Joint2', format='%.3f', value=a['J2'])                                      
                                            ui.number('Joint3', format='%.3f', value=a['J3'])                                      
                                            ui.number('Joint4', format='%.3f', value=a['J4'])                                      
                                            ui.number('Joint5', format='%.3f', value=a['J5'])                                      
                                            ui.number('Joint6', format='%.3f', value=a['J6'])
                                            ui.number('Gripper', format='%.0f', value=a['Gripper'])                                     
                                            # ui.number('Delay', format='%.3f', value=a['Delay'])                                      

    def update(data):
        #data = client.get_buffer_data()
        if data is None:
            info_status.set_text(f'CAN BUS: Not enabled')
            info_status.style('color: #fc0320; font-weight: bold')
        else:
            info_status.set_text(f'CAN BUS: Enabled')
            info_status.style('color: #03fc1c; font-weight: bold')
            # Split the string by spaces and convert each hexadecimal value to an integer
            int_values = [int(x, 16) for x in data.split()]
            byte_array = struct.pack('12B', *int_values)
            # print(int_values, byte_array)
            if len(byte_array) == 12:
                msg = can_data.pack_can_message(byte_array)
                # print(msg)
                count = 0
                id = msg.get('id')
                if id >= 0x30: print('CAN BUS ID MUST less than 48(0x30)!!!')
                for k,v in motors_cfg.items():
                    count += 1
                    if k == 'M'+str(count) and count == id:
                        type = msg.get('type')
                        body = msg.get('body')
                        if type == can_data.command_id['Get_Encoder_Estimates']:
                            pos, vel = struct.unpack('<ff', body)
                            # current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                            # buffer.append((current_time, pos))
                            # check_and_print_buffer()
                            r_v = get_reduction(id - 1)
                            v['position'] = (360.0 * pos)/ r_v
                            with joint_angle_lock:
                                joint_angle_tmp['J'+str(count)] = (360.0 * pos)/ r_v
                            v['velocity'] = vel
                            if id == 5 and v['teaching'] == 1: 
                                 teaching.append(pos)
                                #  print(v['teaching'])
                        elif type == can_data.command_id['Heartbeat']:
                            error, state, result, traj_done, reserved = struct.unpack('<IBBBB', body)
                            if result == 0:
                                v['status'] = state
                                v['error'] = error
                        elif type == can_data.command_id['Get_Bus_Voltage_Current']:
                             vol, iq = struct.unpack('<ff', body)
                             v['voltage'] = round(vol, 2)
                             v['ibus'] = iq
                        elif type == can_data.command_id['Get_Iq']:
                             iqs, iq = struct.unpack('<ff', body)
                            #  v['ibus'] = iqs
                             v['iq'] = iq 
                        elif type == can_data.command_id['Get_Temperature']:
                             f, m = struct.unpack('<ff', body)
                             print(f, m)
    # ui.timer(0.01, update)
    # ui.timer.cancel
    update_list()

