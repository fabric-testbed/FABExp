import os
import re
import json
import traceback
from fabrictestbed_extensions.fablib.fablib import FablibManager as fablib_manager
from mflib.mflib import MFLib
try:
    fablib = fablib_manager()                
    #fablib.show_config()
except Exception as e:
    print(f"Exception: {e}")
    
def set_state_local(state):
    this = os.path.dirname(os.path.realpath(__file__))
    relative_path = '../../runtime_info/cur_state_info/state.json'
    file_path = os.path.abspath(os.path.join(this, relative_path))
    try:
        with open(file_path, 'r') as file:
            existing_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        existing_data = {}  
    slice_name = state.get('slice_name')
    if slice_name in existing_data:
        
        existing_data[slice_name]['state'] = state['state']
    else:
        
        existing_data[slice_name] = {'state': state['state']}
    with open(file_path, 'w') as file:
        json.dump(existing_data, file, indent=2)
        
def update_state_local(slice_name, new_value):
    this = os.path.dirname(os.path.realpath(__file__))
    relative_path = '../../runtime_info/cur_state_info/state.json'
    file_path = os.path.abspath(os.path.join(this, relative_path))
    try:
        with open(file_path, 'r') as file:
            existing_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        existing_data = {}  

    if slice_name in existing_data:
        if new_value in existing_data[slice_name]['state']:
            print (f'{new_value} already in state')
        else:
            existing_data[slice_name]['state'].append(new_value)
    else:
        existing_data[slice_name] = {'state': [new_value]}

    with open(file_path, 'w') as file:
        json.dump(existing_data, file, indent=2)
        
def read_state_from_local(slice_name):
    this = os.path.dirname(os.path.realpath(__file__))
    relative_path = '../../runtime_info/cur_state_info/state.json'
    file_path = os.path.abspath(os.path.join(this, relative_path))
    try:
        with open(file_path, 'r') as file:
            existing_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        existing_data = {}  

    if slice_name in existing_data:
        return {'slice_name':slice_name, 'state':existing_data[slice_name]['state']}
    else:
        return None
        
def update_state_in_fim(slice_name, state):
    try:
        slice = fablib.get_slice(name=slice_name.replace("'", "").replace("\"", ""))
    except Exception as e:
        print(f"Fail: {e}")
        return
    if state is not None:
        for node in slice.get_nodes():
            node.set_user_data(user_data=state)
    try:
        # Submit Slice Request
        print(f'Submitting the slice, "{slice_name}" to update state {state}...')
        slice.submit(wait_interval=60)
        print(f'{slice_name} creation done.')

    except Exception as e:
        print(f"Slice Fail: {e}")
        traceback.print_exc()
        
def get_state_in_fim(slice_name):
    try:
        slice = fablib.get_slice(name=slice_name.replace("'", "").replace("\"", ""))
    except Exception as e:
        print(f"Fail: {e}")
        return
    node_states = []
    for node in slice.get_nodes():
        #print (node.get_name())
        #print (node.get_user_data())
        data= node.get_user_data()
        if ('slice_name' in data and 'state' in data):
            filtered_json_data = {key: data[key] for key in ['slice_name', 'state']}
            filtered_json_string = json.dumps(filtered_json_data, indent=2)
            node_states.append(filtered_json_string)
        else:
            print (f'Cannot find slice_name or state in the data in the user data of {node.get_name()}')
    if (all(x == node_states[0] for x in node_states)):
        return node_states[0]
    else:
        print ('state inconsistency')
        return
    