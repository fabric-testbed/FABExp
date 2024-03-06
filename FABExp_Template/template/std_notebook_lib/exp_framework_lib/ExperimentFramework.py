#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2020 FABRIC Testbed
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Author: Pinyi Shi

from fabrictestbed_extensions.fablib.fablib import FablibManager as fablib_manager
from collections import OrderedDict
from IPython.core.getipython import get_ipython
import ipywidgets as widgets
from IPython.display import display, Markdown
from ipywidgets import HTML, Layout
import threading, paramiko
from pathlib import Path
import datetime
import state
import logging
import configparser
import time
import os
import sys
import re
import json
import requests
import nbformat
import subprocess
import logging
import shutil

class ExperimentFramework():
    __version__ = '0.1.2'
    
    
    def __init__(self,src=None, file_path=None):
        self.get_config_file_path(file_path)
        self.src=src
        self.path_structure= self.read_config(self.config_file_path)
        #print (self.path_structure)
        try:
            self.fablib = fablib_manager()  
        except Exception as e:
            #print(f"Exception: {e}")
            raise Exception("Failed to initialize ExperimentFramework: " + str(e))
        self.slice_loader = None
        #self.node_ssh_cmds = None
        self.fabric_slice_names = self.get_submitted_slice_names()
        self.log_file_path = self.path_structure['Log']['LOG_FILE']
        self.set_up_logger()
        self.get_dependencies()
        self.slice_selected = False
        self.slice_submitted = widgets.Checkbox(value=False, description='ssubmitted')
        self.selected_slice_name =widgets.Text(value='none', description='sname')
        self.selected_slice_name.observe(self.update_state_info_widget, names='value')
        self.selected_slice_name.observe(self.update_config_widget, names='value')
        self.slice_submitted.observe(self.update_state_info_widget, names='value')
        self.slice_submitted.observe(self.update_config_widget, names='value')
        self.selected_slice_state = widgets.Text(value='none', description='state')
        self.selected_slice_state.observe(self.update_state_info_widget, names='value')
        self.selected_slice_state.observe(self.update_mflib_notebooks_widget,names='value')
        self.selected_slice_state.observe(self.update_mflib_service_widget,names='value')
        self.selected_slice_state.observe(self.update_view_measurements_tab_widget,names='value')
        self.selected_slice_state.observe(self.update_config_widget, names='value')
        self.fim_state = 'none'
        self.default_JH_path = "/home/fabric/work"
        self.JH_home_path = "/home/fabric"
        self.fabric_api = 'https://uis.fabric-testbed.net'
        self.jupyter_examples_dirs= self.get_existing_jupyter_examples_dirs()
        self.file_existence=True
        self.selected_configure_notebook = None
        self.slice_info_checkbox = {'random sites': False, 'random ptp sites': False, 'generate graphml': False, 'post boot script': False}
        self.mflib_service_checkbox = {'ELK Stack': False, 'Prometheus': False, 'Precision Timing': False, 'Data Transfer service': False, 'One-Way-Latency (OWL)': False}
            
        self.slice_loaded = widgets.Checkbox(value=False)
        self.slice_loaded.observe(self.on_load_change, names='value')
        self.slice_info_tab_widget = self.slice_info_tab()
        self.prerequiste_tab_widget = self.prerequisite_tab()
        self.config_widget = self.configuration_software_tab_original()
        self.mflib_service_tab_widget = self.mflib_service_tab()
        self.run_notebooks_tab_widget = self.run_notebooks_tab()
        self.view_output_tab_widget = self.view_output_tab()
        self.view_measurements_tab_widget = self.view_measurements_tab()
        self.slice_state_tab_widget = self.slice_state_tab()
        self.main_tab = widgets.Tab()
        self.main_tab.children = [self.prerequiste_tab_widget, self.slice_info_tab_widget,self.config_widget, self.mflib_service_tab_widget, self.run_notebooks_tab_widget,self.view_output_tab_widget, self.view_measurements_tab_widget, self.slice_state_tab_widget ]
        self.main_tab.set_title(0, '1.Check Prereqs')
        self.main_tab.set_title(1, '2.Slice Info')
        self.main_tab.set_title(2, '3.Config_S/W')
        self.main_tab.set_title(3, '4.MFLib Services')
        self.main_tab.set_title(4, '5.Run Experiments')
        self.main_tab.set_title(5, '6.View Output')
        self.main_tab.set_title(6, 'See Measurements')
        self.main_tab.set_title(7, 'Slice State')

    
    # Set up logger which writes to both the log file and stdout   
    def set_up_logger(self):
        """
        Creates logger that writes to both the log file and stdout
        
        """
        module_path = os.path.abspath(__file__)
        logger_name = module_path.replace(os.sep, '.').replace('.py', '') +str(time.time())
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)
        filehandler = logging.FileHandler(self.log_file_path)
        filehandler.setLevel(logging.DEBUG)
        streamhandler= logging.StreamHandler(sys.stdout)
        streamhandler.setLevel(logging.DEBUG)
        filehandler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        streamhandler.setFormatter(logging.Formatter(
            '%(message)s'
        ))
        self.logger.addHandler(filehandler)
        self.logger.addHandler(streamhandler)
        
    
    def get_ssh_cmd_from_slice(self, n_list):
        result_dict = {}
        for n in n_list:
            name = n.get_name()
            cmd = n.get_ssh_command()
            result_dict[name] = cmd
        return result_dict
    
    def get_slice_state(self, slice_name):
        try:
            sl = self.fablib.get_slice(name = slice_name)
            st = sl.get_state()
            return st
        except Exception as e:
            self.logger.info(f"Fail to get the state of slice: {e}")
    
    
    def open_terminal(self, b, nb_path, output):
        with output:
            output.clear_output()
            print ('start open terminal:' + str(datetime.datetime.now()))
            cmd = self.slice_loader.get_node(name=self.run_notebooks_tab_widget.children[4].children[1].children[0].value).get_ssh_command()
            print (str(datetime.datetime.now()))
            #cmd = self.node_ssh_cmds[self.run_notebooks_tab_widget.children[4].children[1].children[0].value]
            os.environ['SSH_CMD'] = cmd
            #ssh_cmd =cmd
            self.run_notebook(nb_path)
            print ('end open terminal:' + str(datetime.datetime.now()))
            output.clear_output()
    
    
    def list_files(self, directory):
        """
        List the files in a directory

        :return: file names in a list
        :rtype: List
        """
        return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f)) and not f.startswith('.')]
    
    
    def list_slice_dirs(self, directory_path):
        """
        List all saved slice folder names in the slice_info dir .

        
        :return: List of directory names
        :rtype: List
        """
        slice_dirs = [name for name in os.listdir(directory_path)
                    if os.path.isdir(os.path.join(directory_path, name)) and not name.startswith('.') and not name.startswith('_')]
        return slice_dirs
    
    
    def backup_slice_info(self, directory_path, folder_name, file1_name, file2_name):
        """
        Checks if a folder(named after slice name) exists in a directory, and either clears it or creates it.
        Then, copy two specified files(define_slice, topo_variables) into this folder.

        """
        folder_path = os.path.join(directory_path, folder_name)

        # Check if the folder exists
        if os.path.exists(folder_path):
            # remove all files in the folder
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    self.logger.info(f'Failed to delete {file_path}. Reason: {e}')
        else:
            # if slice folder does not exist, create the folder
            os.makedirs(folder_path)

        # Move the two files into the folder
        for file_name in [file1_name, file2_name]:
            source_path = os.path.join(directory_path, file_name)
            destination_path = os.path.join(folder_path, file_name)
        
            # Check if the file exists before copy
            if os.path.exists(source_path):
                shutil.copy(source_path, destination_path)
            else:
                self.logger.info(f'File {file_name} does not exist in the directory.')
                
    
    
    
    
    
    def copy_files_back(self, folder_name, file1_name, file2_name, directory_path):
        """
        Copy define_slice.ipynb and topology_variables.ipynb back from the slice folder back to slice_info

        """
        folder_path = os.path.join(directory_path, folder_name)

        # Check if the folder exists
        if os.path.exists(folder_path):
            for file_name in [file1_name, file2_name]:
                file_path = os.path.join(folder_path, file_name)
                try:
                    if os.path.isfile(file_path):
                        destination_path = os.path.join(directory_path, file_name)
                        shutil.copy(file_path, destination_path)
                    else:
                        self.logger.info(f'Failed to find file {file_path}') 
                except Exception as e:
                    self.logger.info(f'Failed to copy {file_path}. Reason: {e}')
        else:
            self.logger.info(f'Failed to find {folder_path}')
                        
    
    def update_view_measurements_tab_widget(self, change):
        """
        Updates the view measurements tab
        Called by the checkboxes e.g, mflib service and current state, in the observe function  
        """
        #print ('start update meas wid:' + str(datetime.datetime.now()))
        view_elk_nb_path = self.path_structure['Instrumentize']['MFLIB_VIEW_ELK_NOTEBOOK']
        view_prom_nb_path = self.path_structure['Instrumentize']['MFLIB_VIEW_PROMETHEUS_NOTEBOOK']
        op = widgets.Output()
        op.clear_output()
        
        t1 = 'click to open and view ELK measurement notebook'
        t2 = 'click to open and view Prometheus measurement notebook'
        
        if self.src:
            elk_path = self.get_relative_path_with_parent(view_elk_nb_path)
            prom_path = self.get_relative_path_with_parent(view_prom_nb_path)
        else:
            elk_path = self.get_relative_path(view_elk_nb_path)
            prom_path = self.get_relative_path(view_prom_nb_path)
        #with op:
            #op.clear_output()
            #display(Markdown(f"[{t1}]({elk_path})"))
            #display(Markdown(f"[{t2}]({prom_path})"))
        
        if isinstance(change['owner'], widgets.Checkbox):
            self.mflib_service_checkbox[change['owner'].description] = change.new
        
        if (self.selected_slice_state.value != 'none'):
            try:
                s = json.loads(self.selected_slice_state.value)
            except Exception as e:
                print(f"Exception: {e}")
            if s:
                if (self.mflib_service_checkbox['ELK Stack'] and self.mflib_service_checkbox['Prometheus']):
                    text = 'You have selected both ELK and Prometheus<br>'
                    if "ELK_INSTRUMENTIZED" not in s['state']:
                        text += 'Please instrumentize ELK<br>'
                    else:
                        text += 'ELK is instrumentized<br>'
                        #text+= 'You can run the following notebook to see ELK measurements:<br>'
                        with op:
                            display(Markdown(f"[{t1}]({elk_path})"))
                        
                    if "PROMETHEUS_INSTRUMENTIZED" not in s['state']:
                        text += 'Please instrumentize Prometheus<br>'
                    else:
                        text += 'Prometheus is instrumentized<br>'
                        #text+= 'You can run the following notebook to see Prometheus measurements:<br>'
                        with op:
                            display(Markdown(f"[{t2}]({prom_path})"))
            
                elif (self.mflib_service_checkbox['ELK Stack'] and not self.mflib_service_checkbox['Prometheus']):
                    text = 'You have selected ELK<br>'
                    if "ELK_INSTRUMENTIZED" not in s['state']:
                        text += 'Please instrumentize ELK<br>'
                    else:
                        text += 'ELK is instrumentized<br>'
                        with op:
                            display(Markdown(f"[{t1}]({elk_path})"))
                elif (not self.mflib_service_checkbox['ELK Stack'] and self.mflib_service_checkbox['Prometheus']):
                    text = 'You have selected Prometheus<br>'
                    if "PROMETHEUS_INSTRUMENTIZED" not in s['state']:
                        text += 'Please instrumentize Prometheus<br>'
                    else:
                        text += 'Prometheus is instrumentized<br>'
                        with op:
                            display(Markdown(f"[{t2}]({prom_path})"))
                else:
                    text = 'You have selected neither ELK nor Prometheus<br>'
            children = self.view_measurements_tab_widget.children        
            new_child = widgets.VBox([widgets.HTML(value=text), op])
            new_children = (children[0], new_child, children[2])
            self.view_measurements_tab_widget.children = new_children
            
        else:
            text = 'No state found<br>'
            children = self.view_measurements_tab_widget.children
            new_child = widgets.VBox([widgets.HTML(value=text)])
            new_children = (children[0], new_child, children[2])
            self.view_measurements_tab_widget.children = new_children
            
        #print ('end update meas wid:' + str(datetime.datetime.now()))
            
    
    def get_dependencies(self):
        """
        Reads info, e.g, prerequisite state, related notebooks, notebook headers from the dependency file

        """
        dependency_file_path = self.path_structure['Setup']['DEPENDENCY_FILE']
        with open(dependency_file_path, 'r') as file:
            data = json.load(file)
        #self.notebook_headers= data['notebook_headers']
        self.state_dependencies = data['state_dependencies']
        self.experiment_prerequisite_states = data['experiment_prerequisite_states']
        self.notebooks_collection = data['notebooks_collection']
    
    def get_notebook_path(self, nb_name):
        """
        Finds the notebook path in the config data based on the name

        :return: notebook absolute path
        :rtype: String
        """
        for k, v in self.path_structure.items():
            if nb_name in v:
                return v[nb_name]
    
    def get_notebook_collection(self, exp_name):
        """
        Returns the notebook names associated with an experiment

        :return: notebook names in a list
        :rtype: List
        """
        for k, v in self.notebooks_collection.items():
            if k == exp_name:
                return v
        
        
    def add_and_unique(self, list1, list2):
        """
        Concats two lists and keeps one copy of the unique items

        :return: merged unique list
        :rtype: List
        """
        merged_dict = OrderedDict.fromkeys(list1 + list2)
        result = list(merged_dict.keys())
        return result
    
    def read_state_requirements_from_file(self, exp_name):
        """
        Reads experiment state requiremnts 

        :return: experiment state requirments
        :rtype: List
        """
        for k, v in self.experiment_prerequisite_states.items():
            if k==exp_name:
                return v
            
    def read_state_dependencies_from_file(self, state):
        """
        Reads state dependencies from data

        :return: state info 
        :rtype: Dict
        """
        for k, v in self.state_dependencies.items():
            if k==state:
                return v
        
    def compare_states(self, requirement_state, current_state):
        """
        Calculates the difference of two lists

        :return: list difference
        :rtype: List
        """
        return [item for item in requirement_state if item not in current_state]
    
    
    
    def on_load_change(self, change):
        """
        Observe function for whether a slice is loaded
        If a slice is loaded, hide the widgets for slice options and slice submission
        """
        if change['new']:
            #print ("in the observe func")
            for widget in self.slice_info_tab_widget.children[1].children+self.slice_info_tab_widget.children[2].children:
                widget.layout.visibility = 'hidden'
                widget.layout.display = 'none'
        else:
            for widget in self.slice_info_tab_widget.children[1].children+self.slice_info_tab_widget.children[2].children:
                widget.layout.visibility = 'visible'
                widget.layout.display = ''
            
            
    def get_config_file_path(self, file_path):
        """
        Finds the path of the config file

        """
        if not file_path:
            this_file_location =os.path.abspath(__file__)
            p = Path(__file__).parents[2]
            default_file_location= os.path.join(p, "paths.cfg")
            self.config_file_path = default_file_location
        else: 
            self.config_file_path = file_path
        
    # This function reads the config file and save the paths of files in the package in a dict        
    def read_config(self, file_path):
        """
        Reads the data in the config file

        :return: notebooks full paths in a dict 
        :rtype: Dict
        """
        config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        config.read(file_path)
        file_path_dir = os.path.dirname(file_path)
        dir_list = []
        try:
            for op in config.options("Directories"):
                dir_list.append(op)
        except configparser.NoSectionError:
            raise Exception(f"Section 'Directories' not found in {file_path}")
        config_variables = {}
        interpolated_option_value = ""
        for section in config.sections():
            if section !="Directories":
                for option in config.options(section):
                    option_value = config.get(section, option)
                    for k in dir_list:
                        if k.upper() in option_value:
                            interpolated_option_value = os.path.join(file_path_dir, (option_value % {k.upper(): config.get("Directories", k.upper())}))
                            if section not in config_variables.keys():
                                config_variables[section]={}
                                config_variables[section][option.upper()]= interpolated_option_value 
                            else: 
                                config_variables[section][option.upper()]= interpolated_option_value 
        return config_variables
    
    
    
    def get_existing_jupyter_examples_dirs(self):
        """
        Finds jupyter examples dirs

        :return: dir names in a list
        :rtype: List
        """
        jupyter_examples_dirs = [directory for directory in os.listdir(self.default_JH_path) if os.path.isdir(os.path.join(self.default_JH_path, directory)) and directory.startswith("jupyter-examples-rel")]
        return sorted(jupyter_examples_dirs)
    
   
    
    def read_notebook_content(self, notebook_path):
        """
        Reads a jupyter notebook

        :return: notebook content
        :rtype: Dict
        """
        with open(notebook_path, 'r', encoding='utf-8') as notebook_file:
            notebook_content = nbformat.read(notebook_file, as_version=4)
        return notebook_content
    
    
    def extract_code_cells(self, notebook_content):
        """
        Finds the cells that are code type

        :return: cells
        :rtype: Dict
        """
        code_cells = []
        for cell in notebook_content['cells']:
            if cell['cell_type'] == 'code':
                code_cells.append(cell['source'])
        return code_cells
    
    def check_config_nb_type(self, notebook_path):
        self.config_nb_type = 'none'
        nb_content = self.read_notebook_content(notebook_path)
        if nb_content:
            cells = self.extract_code_cells(nb_content)
        else:
            self.logger.info(f'Failed to read notebook')
            return
        if cells:
            if 'fablib_manager(project_id=project_id)' in cells[0]:
                self.config_nb_type = 'config_validate'
            elif 'FABRIC_BASTION_USERNAME' in cells[0]:
                self.config_nb_type = 'config'
            else:
                self.config_nb_type = 'none'
            

    def process_export_line(self, line):
        """
        Finds the lines in configure.ipynb that have export xx == xx
        parse the lines 

        :return: key value tuple
        :rtype: tuple
        """
        # Split the line by "="
        parts = line.split('=')
        # Extract the variable name and value
        variable_name = parts[0].strip().replace('export ', '')
        variable_value = parts[1].strip()
        return variable_name, variable_value
    
    def find_fabric_rc_line(self, code_cells, fabric_rc_name):
        """
        Finds the line in configure.ipynb that specifies the location of the fabric rc file

        :return: line that has fabric rc path
        :rtype: String
        """
        for code_cell in code_cells:
            lines = code_cell.split('\n')
            for line in lines:
                if fabric_rc_name in line:
                    return line
        return None
    
    # Get relative path to be used in the markdown link which opens the notebook
    def get_relative_path(self, absolute_path, base_path='.'):
        """
        Given an absolute path, calculates the relative path

        :return: relative path
        :rtype: String
        """
        return os.path.relpath(absolute_path, base_path)
    
    def get_parent_dir(self, arg1, arg2):
        """
        Compares two paths

        :return: parent name
        :rtype: String
        """
        components1 = arg1.split('/')
        components2 = arg2.split('/')
        components1 = [i for i in components1 if i != '..']
        index = components2.index(components1[0])
        return components2[index - 1]
    
    def get_relative_path_with_parent(self, absolute_path, base_path='.'):
        """
        Builds the relative path using parent dir name

        :return: relative path
        :rtype: String
        """
        relative_path = os.path.relpath(absolute_path, base_path)
        parent = self.get_parent_dir(relative_path, absolute_path)
        return (f'./{parent}/{relative_path}')
    
    
    
    def extract_exports(self, code_cells):
        """
        Finds the cells that are code type

        :return: export values in configure.ipynb
        :rtype: Dict
        """
        exports = {}
        exports_in_cat = ''
        for code_cell in code_cells:
            file_cat = False
            lines = code_cell.split('\n')
            for line in lines:
                if line.startswith('cat <<EOF >'):
                    file_cat = True
                if line.strip().startswith('EOF'):
                    file_cat = False
                if line.startswith('export') and '=' in line and not file_cat:
                    name, value = self.process_export_line(line)
                    exports[name] = value
        return exports
    
    # Reads the selected configure.ipynb and reads the variables and values
    def get_environment_variables(self, notebook_path, home_path):
        """
        Calculates actual path by replacing symbols e.g, $HOME with actual path

        :return: variable path info
        :rtype: Dict
        """
        content=self.read_notebook_content(notebook_path)
        code_cells = self.extract_code_cells(content)
        exports=self.extract_exports(code_cells)
        # Replace '${HOME}' with home_path
        for key, value in exports.items():
            if '${HOME}' in value:
                exports[key] = value.replace('${HOME}', home_path)
        # Remove the single quotes
        for key, value in exports.items():
            if "'" in value:
                exports[key] = value.replace("'", "")
        # Replace ${key} with the actual value
        for key, value in exports.items():
            for k, v in exports.items():
                pattern = f"${{{k}}}"
                value = value.replace(pattern, v)
            exports[key] = value
        
        return exports
    

    def find_content_in_cat(self, notebook_path, home_path, variable_dict):
        """
        Reads the notebook find the cat sections, assert the content in the files

        :return: content in cat block
        :rtype: List
        """
        content=self.read_notebook_content(notebook_path)
        code_cells = self.extract_code_cells(content)
        final_data=[]
        for code_cell in code_cells:
            data={}
            cat_cell=False
            file_name = ''
            lines = code_cell.split('\n')
            for line in lines:
                line.strip()
            if lines[0].startswith('cat <<EOF >') and lines[-1].startswith('EOF'):
                cat_cell=True
                file_name = lines[0].split('>')[1].strip()
                data['name']=file_name
                data['content']=lines[1:-1]
                final_data.append(data)
            
        #variable_dict = self.get_environment_variables(notebook_path, home_path)
   
        for key, value in variable_dict.items():
            for item in final_data:
                if (f"${{{key}}}" in item['name']):
                    item['name']= value
        
        for key, value in variable_dict.items():
            for item in final_data:
                for i, content_item in enumerate(item['content']):
                    if f"${{{key}}}" in content_item:
                        item['content'][i] = content_item.replace(f"${{{key}}}", value)
                    if '${HOME}' in content_item:
                        item['content'][i] = content_item.replace('${HOME}', home_path)
        return final_data  
    
    def get_selected_congigure_notebook_path(self):
        """
        Calculates the path of the configure.ipynb notebook 
        :return: configure.ipynb path
        :rtype: String
        """
        selected_configure_notebook_path = os.path.join(self.default_JH_path, self.selected_JH_dir, "configure.ipynb")
        return (selected_configure_notebook_path)
        
    def get_selected_requirement_txt_path(self):
        """
        Calculates the path of requirements.txt

        :return: requirements.txt path
        :rtype: String
        """
        config_notebook_dir = os.path.dirname(self.selected_configure_notebook)
        selected_requirements_txt_path = os.path.join(config_notebook_dir, "requirements.txt")
        return selected_requirements_txt_path
    
    
    def check_file_existence(self, file_path):
        """
        Check the existence of a file given the path

        :return: file exists or not
        :rtype: Bool
        """
        if os.path.exists(file_path):
            return True
        else:
            self.file_existence=False
            return False
            
    
    def check_file_content(self, file_path, content):
        """
        Check whether the content is the same in the file

        :return: content same or not
        :rtype: Bool
        """
        try:
            with open(file_path, 'r') as file:
                file_content = file.read().splitlines()
                if (file_content == content):
                    return True
                else:
                    print(f"Content mismatch in file: {file_path}")
                    for line_num, (actual, expected) in enumerate(zip(file_content, content), start=1):
                        if actual != expected:
                            self.logger.info(f"Line {line_num}: Expected '{expected}', Got '{actual}'")
                            self.logger.info('Make sure you have run configure.ipynb in Step 1')
                            
                    return False
        except FileNotFoundError:
            self.logger.info(f"File not found: {file_path}")
            return False
        
    def check_bashion_name(self, rc_file_path):
        """
        Check the bashion user name in the fabric rc file, whether it is empty or default value

        """
        with open(rc_file_path, 'r') as f:
            for line in f:
                if "export FABRIC_BASTION_USERNAME" in line:
                    parts = line.split('=')
                    value = parts[1].strip()
        if value:
            if value != "<YOUR_BASTION_USERNAME>":
                self.logger.info(f"FABRIC_BASTION_USERNAME is set to {value} in the fabric_rc file")
            else:
                self.logger.info("Open configure.ipynb to set FABRIC_BASTION_USERNAME")
        else:
            self.logger.info("Run configure.ipynb to set FABRIC_BASTION_USERNAME")
        
        
    def check_project_id(self, rc_file_path, token_path, uuid):
        """
        Calls fabric core api to get the uuid using the token
        Uses the uuid to get project lists the user belongs to
        Checks in fabric rc file whether the project id is in the returned list
        """
        with open(rc_file_path, 'r') as f:
            for line in f:
                if "export FABRIC_PROJECT_ID" in line:
                    parts = line.split('=')
                    value = parts[1].strip()
        if value:
            if value != "<YOUR_PROJECT_ID>":
                self.logger.info(f"FABRIC_PROJECT_ID is set to {value} in the fabric_rc file")
                correct = False
                time.sleep(2)
                project_list = self.fabric_api_project_list(token_path, uuid)
                time.sleep(2)
                self.logger.info('You are in the following projects:')
                self.logger.info(project_list)
                for p in project_list:
                    if (p['uuid']== value):
                        self.logger.info(f"Project id {value} in {rc_file_path} matches project {p['name']}")
                        correct = True
                if (correct is False):
                    self.logger.info(f'Project id {value} is not valid')
                    self.logger.info('Go to Step 1 and set the correct project id')
                    return       
            else:
                self.logger.error("You project value is <YOUR_PROJECT_ID>. Run configure.ipynb to set FABRIC_PROJECT_ID")
        else:
            self.logger.error("Run configure.ipynb to set FABRIC_PROJECT_ID")
            
    def check_key_expiration(self, token_path, uuid):
        """
        Check the keys using the fabric core api, whether they expires in 30 days or already expired

        """
        keys = self.fabric_api_ssh_keys(token_path, uuid)
        time.sleep(3)
        if (len(keys)>0):
            for k in keys:
                if ('expire' in list(k.keys())):
                    expires_on_str = k['expire']
                    expires_on = datetime.datetime.strptime(expires_on_str, '%Y-%m-%d %H:%M:%S.%f%z')
                    days_difference = (expires_on - datetime.datetime.now(expires_on.tzinfo)).days
                    if (days_difference<0):
                        self.logger.error(f"!!! Your key {k['name']} of type {k['type']} has expired")
                        self.logger.info("Go to the 'fabric portal-experiments-manage ssh keys' to update your key")
                        return
                    elif (days_difference < 30):
                        self.logger.warning(f"!!!WARNING:Your key {k['name']} of type {k['type']} will expire in less than 30 days. Details can be found below:")
                        self.logger.info(k)
                    else:
                        self.logger.info('The key below looks good.')
                        self.logger.info(k)
                        
            
    def fabric_api_uuid(self, token_path):
        """
        Calls the fabric core api using the token to get uuid

        :return: uuid
        :rtype: String
        """
        try:
            self.logger.info(f'Calling the Fabric core api to get the uuid using the token file {token_path}')
            with open(token_path, 'r') as file:
                token_data = json.load(file)
            if ('id_token' in list(token_data.keys())):
                id_token = token_data['id_token']
            else:
                self.logger.error("The format of the token file is incorrect. No 'id_token' key found")
                return
            #fabric_api_url = 'https://uis.fabric-testbed.net'
            url = self.fabric_api + '/whoami'
            headers = {
                'Authorization': 'Bearer ' + str(id_token),
                'Accept': 'application/json'
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.uuid = data['results'][0]['uuid']
                self.logger.info(f"Got uuid {self.uuid}")
                self.logger.info("\n")
                return self.uuid
            else:
                self.logger.error(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            
            
    def fabric_api_project_list(self, token_path, uuid):
        """
        Calls the fabric core api using uuid to get project list

        :return: project list
        :rtype: List
        """
        try:
            self.logger.info(f'Calling the Fabric core api to get the project list using uuid')
            projects = []
            with open(token_path, 'r') as file:
                token_data = json.load(file)
            id_token = token_data['id_token']
            #fabric_api_url = 'https://uis.fabric-testbed.net'
            url = self.fabric_api+'/projects?exact_match=false&offset=0&limit=5&person_uuid='+uuid+'&sort_by=name&order_by=asc'
            headers = {
                'Authorization': 'Bearer ' + str(id_token),
                'Accept': 'application/json'
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                pjs = data['results']
                for p in pjs:
                    projects.append({'name': p['name'], 'uuid':p['uuid']})
                return projects
            else:
                self.logger.error(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            
    def fabric_api_ssh_keys(self, token_path, uuid):
        """
        Calls the fabric core api using uuid to get ssh key lists

        :return: ssh key list
        :rtype: List
        """
        try:
            self.logger.info(f'Calling the Fabric core api to get ssh keys using the uuid')
            keys = []
            with open(token_path, 'r') as file:
                token_data = json.load(file)
            id_token = token_data['id_token']
            #fabric_api_url = 'https://uis.fabric-testbed.net'
            url = self.fabric_api+'/sshkeys?person_uuid='+uuid
            headers = {
                'Authorization': 'Bearer ' + str(id_token),
                'Accept': 'application/json'
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                ks = data['results']
                for k in ks:
                    keys.append({'name': k['comment'], 'type': k['fabric_key_type'], 'expire':k['expires_on']})
                return keys
            else:
                self.logger.error(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
        

    def create_info_icon(self, tooltip):
        icon_html = f'<span title="{tooltip}" style="cursor: help; font-size: 120%; margin-left: 5px;"><i class="fa fa-info-circle" aria-hidden="true"></i></span>'
        return widgets.HTML(value=icon_html)
    
    def on_checkbox_change(self, change):
        self.logger.info(f"{change['owner'].description}: {change['new']}")

        
                
    def on_button_click_prerequisite_step2(self, b, output, home_path):
        """
        Button on click function to check the existence of files specified in configure.ipynb

        """
        if not self.selected_configure_notebook:
            with output:
                output.clear_output()
                self.logger.info("Finish Step1 first")
                return
        self.file_existence = True    
        notebook_path = self.selected_configure_notebook
        variables = self.get_environment_variables(notebook_path, home_path)
        con = self.find_content_in_cat(notebook_path, home_path, variables)
        variables_to_check=['FABRIC_BASTION_PRIVATE_KEY_LOCATION',
                            'FABRIC_BASTION_SSH_CONFIG_FILE',
                            'FABRIC_RC_FILE',
                            'FABRIC_TOKEN_FILE',
                            'FABRIC_SLICE_PRIVATE_KEY_FILE',
                            'FABRIC_SLICE_PUBLIC_KEY_FILE'
                            ]
        with output:
            output.clear_output()
            for v in variables_to_check:
                if v in variables.keys():
                    p = variables[v]
                check_result = self.check_file_existence(p)
                if (check_result is False):
                    self.file_existence = False
                check_mark = "&#9989;" if check_result else "&#10060;"
                color = "green" if check_result else "red"
                item_html = f'<span style="color: {color}; font-size: 12px;">{check_mark} {v} exists at {p}</span>'
                display(HTML(item_html))
            if (self.file_existence is False):
                self.logger.error("Make sure you have run configure.ipynb in Step 1!")
            else:
                self.logger.info("All files found! Go to Step 3")
    
    
    
    
    
    def on_button_click_prerequisite_step3(self, b, output, home_path):
        """
        Button on click function to check whether content of files are correct

        """
        if not self.selected_configure_notebook:
            with output:
                output.clear_output()
                self.logger.error("Finish Step1 first")
                return  
        if (self.file_existence is False):
            with output:
                output.clear_output()
                self.logger.error("Go back to Step 1!")
                return 
        else:
            with output:
                output.clear_output()
                #print ('Checking content of files...')
                notebook_path = self.selected_configure_notebook
                variables = self.get_environment_variables(notebook_path, home_path)
                con = self.find_content_in_cat(notebook_path, home_path, variables)
                variables_to_check=['FABRIC_RC_FILE',
                            'FABRIC_TOKEN_FILE'
                            ] 
                for v in variables_to_check:
                    if v in variables.keys():
                        if (v == "FABRIC_RC_FILE"):
                            rc_file_path = variables[v]
                        elif (v == "FABRIC_TOKEN_FILE"):
                            token_path = variables[v]
                uuid=self.fabric_api_uuid(token_path)
                if uuid:
                    self.logger.info('Checking project id...')
                    self.check_project_id(rc_file_path, token_path, uuid)
                    self.logger.info('\n')
                    self.logger.info('Checking ssh keys...')
                    self.check_key_expiration(token_path, uuid)
                    self.logger.info('\n')
                    self.logger.info('Checking bashion user name(only checks empty or non-modified default values)...')
                    self.check_bashion_name(rc_file_path)
                    self.logger.info('\n')
                    self.logger.info("Checking FABRIC_RC_FILE...")
                    re = self.check_file_content(con[0]['name'], con[0]['content'])
                    if re:
                        self.logger.info("FABRIC_RC_FILE looks correct")
                    else: 
                        return
                    self.logger.info('\n')
                    self.logger.info("Checking FABRIC_BASTION_SSH_CONFIG_FILE...")
                    re1 = self.check_file_content(con[1]['name'], con[1]['content'])
                    if re1:
                        self.logger.info("FABRIC_BASTION_SSH_CONFIG_FILE looks correct")
                    else:
                        return
                else:
                    return
                
                
            
    def prerequisite_step1_button3(self, b, output):
        """
        Button on click function to open link for configure.ipynb

        """
        
        if not self.selected_configure_notebook:
            with output:
                output.clear_output()
                self.logger.error("Please specify the location of configure.ipynb above")
        else:
            #p = os.path.dirname(self.selected_configure_notebook)
            #get_ipython().run_line_magic('cd', p)
            configure_notebook_relative_path = self.get_relative_path(self.selected_configure_notebook)
            with output:
                output.clear_output()
                display(Markdown(f"[Open the notebook using this link and change values]({configure_notebook_relative_path}) "))    
      
        
    def prerequisite_step1_button1(self, b, output, dropdown):
        """
        Button on click function to check the existence of configure.ipynb in dropdown of jupyter examples dirs

        """
        self.selected_directory = dropdown.value
        if self.selected_directory != 'none':
            self.config_nb_dir = True
            
            configure_notebook_path= os.path.join(self.default_JH_path, self.selected_directory, "configure.ipynb")
            configure_validate_notebook_path= os.path.join(self.default_JH_path, self.selected_directory, "configure_and_validate.ipynb")
            exist = os.path.exists(configure_notebook_path)
            exist1 = os.path.exists(configure_validate_notebook_path)
            with output:
                output.clear_output()
                if exist and exist1:
                    self.logger.info(f'Found both {configure_validate_notebook_path} and {configure_notebook_path}')
                    self.logger.info(f'Selected {configure_validate_notebook_path} based on priority')
                    self.selected_configure_notebook = configure_validate_notebook_path
                    tp = self.check_config_nb_type(self.selected_configure_notebook)
                        
                elif exist1:
                    self.logger.info(f'Only found {configure_validate_notebook_path}')
                    self.logger.info(f'Selected {configure_validate_notebook_path}')
                    self.selected_configure_notebook = configure_validate_notebook_path
                    tp = self.check_config_nb_type(self.selected_configure_notebook)
                elif exist:
                    self.logger.info(f'Only found {configure_notebook_path}')
                    self.logger.info(f'Selected {configure_notebook_path}')
                    self.selected_configure_notebook = configure_notebook_path
                    tp = self.check_config_nb_type(self.selected_configure_notebook)
                else:
                    self.logger.error(f'No configure.ipynb or configure_and_validate.ipynb found in {os.path.join(self.default_JH_path,self.selected_directory)}')
                    
                if (self.config_nb_type == 'config_validate'):
                    for widget in self.prerequiste_tab_widget.children[1].children+self.prerequiste_tab_widget.children[2].children+self.prerequiste_tab_widget.children[3].children:
                        widget.layout.visibility = 'hidden'
                        widget.layout.display = 'none'
                    self.prerequiste_tab_widget.children[0].children[12].on_click(lambda b: self.run_notebook_using_btn_no_state(b, self.selected_configure_notebook, self.prerequiste_tab_widget.children[0].children[13]))
                elif (self.config_nb_type == 'config' or self.config_nb_type == 'none'):
                    for widget in self.prerequiste_tab_widget.children[1].children+self.prerequiste_tab_widget.children[2].children+self.prerequiste_tab_widget.children[3].children:
                        widget.layout.visibility = 'visible'
                        widget.layout.display = ''
                    self.prerequiste_tab_widget.children[0].children[12].on_click(lambda b: self.prerequisite_step1_button4(b, self.prerequiste_tab_widget.children[0].children[13]))
                    
                
        else:
            with output:
                output.clear_output()
                self.logger.error("please select the right directory")
                self.config_nb_dir= False
                return
    
    def prerequisite_step1_button2(self, b, output, textbox):
        """
        Button on click function to check the existence of configure.ipynb in user input dir

        """
        self.custom_config_nb_path = textbox.value
        if self.custom_config_nb_path:
            #self.config_nb_dir = True
            exist = os.path.exists(self.custom_config_nb_path)
            with output:
                output.clear_output()
                if exist:
                    self.logger.info(f'Selected {self.custom_config_nb_path}')
                    self.selected_configure_notebook = self.custom_config_nb_path
                    tp = self.check_config_nb_type(self.selected_configure_notebook)
                else:
                    self.logger.error(f'{self.custom_config_nb_path} does not exist')
                if (self.config_nb_type == 'config_validate'):
                    for widget in self.prerequiste_tab_widget.children[1].children+self.prerequiste_tab_widget.children[2].children:
                        widget.layout.visibility = 'hidden'
                        widget.layout.display = 'none'
                    self.prerequiste_tab_widget.children[0].children[12].on_click(lambda b: self.run_notebook_using_btn_no_state(b, self.selected_configure_notebook, self.prerequiste_tab_widget.children[0].children[13]))
                elif (self.config_nb_type == 'config' or self.config_nb_type == 'none'):
                    for widget in self.prerequiste_tab_widget.children[1].children+self.prerequiste_tab_widget.children[2].children:
                        widget.layout.visibility = 'visible'
                        widget.layout.display = ''
                    self.prerequiste_tab_widget.children[0].children[12].on_click(lambda b: self.prerequisite_step1_button4(b, self.prerequiste_tab_widget.children[0].children[13]))
        else:
            with output:
                output.clear_output()
                self.logger.error("please input the path of the notebook")
                #self.config_nb_dir = False
                
                
    def prerequisite_step1_button4(self, b, output):
        """
        Button on click function to run configure.ipynb

        """
        if not self.selected_configure_notebook:
            with output:
                output.clear_output()
                self.logger.error("Please specify the location of configure.ipynb above")
        else:
            with output:
                output.clear_output(wait=True)
                if (self.config_nb_type == 'config'):
                    self.logger.info("The process may take sometime... ")
                    self.logger.info(f"You should see 'writing xxx bytes to the {self.selected_configure_notebook}' when it finishes with out error")
                    self.logger.info("If there is error, you can find out where the error is in the output below")
                    try:
                        # Execute the notebook using nbconvert
                        result = subprocess.run(
                            f"jupyter nbconvert --to notebook --execute --inplace {self.selected_configure_notebook}",
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
 
                        # Display the output (stdout and stderr)
                        display(HTML(f"<pre>{result.stdout}</pre>"))
                        display(HTML(f"<pre style='color:red;'>{result.stderr}</pre>"))

                    except Exception as e:
                        self.logger.error(f"Error running the notebook: {e}")
        
                
    
       
            
    def on_button_click_prerequisite_step4(self, b, output):
        """
        Button on click function to check whether package version matches in requirements.txt

        """
        if not self.selected_configure_notebook:
            with output:
                self.logger.error("Finish Step1 first")
                return
            
        rq_path=self.get_selected_requirement_txt_path()
        if os.path.exists(rq_path):
            self.logger.info(f'Found {rq_path}')
        else:
            self.logger.info(f'{rq_path} does not exist. Please put requirements.txt in the same dir as configure.ipynb')
            return
        pkg_match =True
        # Clear previous output
        with output:
            output.clear_output()

            # Run 'pip list' command
            result = subprocess.run(['pip', 'list'], stdout=subprocess.PIPE, text=True)

            # Parse the output into a dictionary
            packages = {}
            for line in result.stdout.strip().split('\n')[2:]:
                package_info = line.split()
                package_name = package_info[0]
                package_version = package_info[1]
                packages[package_name] = package_version

        
            #for package, version in packages.items():
                #print(f"{package}: {version}")
            
            with open(rq_path, 'r') as f:
                requirements = [line.strip() for line in f.readlines()]
            reqs = []
            for req in requirements:
                if "==" in req:
                    pkg = req.split("==")[0].strip()
                    vers = req.split("==")[1].strip()
                    if pkg in packages.keys():
                        self.logger.info(f"{pkg} required version:{vers} installed version:{packages[pkg]}" )
                        if (vers!=packages[pkg]):
                            pkg_match = False      
                    else:
                        self.logger.error(f"{pkg} required version:{vers} not installed")
                        pkg_match = False
                elif ">=" in req:
                    pkg = req.split(">=")[0].strip()
                    vers = req.split(">=")[1].strip()
                    if pkg in packages.keys():
                        self.logger.info(f"{pkg} required version:{vers} installed version:{packages[pkg]}" )
                        if (vers!=packages[pkg]):
                            pkg_match = False 
                    else:
                        self.logger.error(f"{pkg} required version:{vers} not installed")
                        pkg_match = False
                else:
                    pkg = req.strip()
                    vers = 'none'
                    if pkg in packages.keys():
                        self.logger.info(f"{pkg} required version:{vers} installed version:{packages[pkg]}" )
                    else:
                        self.logger.error(f"{pkg} required version:{vers} not installed")
                        pkg_match = False
            if (pkg_match == False):
                self.logger.info('\n')
                self.logger.error('Package version mismatch! Go to Step 1 and run configure.ipynb')
            else:
                self.logger.info('\n')
                self.logger.info('Package version check passed!')
            
    # Open notebook link in markdown        
    def slice_info_step1_btn1(self, b, output, real_path):
        """
        Button on click function to display link to open a notebook

        """
        if self.src:
            relative_path = self.get_relative_path_with_parent(real_path)
        else:
            relative_path = self.get_relative_path(real_path)
        with output:
            output.clear_output()
            display(Markdown(f"[Open and modify the notebook using this link]({relative_path})"))
    
    # Open cytoscape editor        
    #def slice_info_step1_btn2(self, b, output, data):
    #    """
    #    Button on click function open cytoscape editor

    #    """
    #    with output:
    #        output.clear_output()
    #        self.desktop = CytoEditor.CytoEditor()
    #        self.desktop.callback = self.update_slice_loaded_or_save_value 
    #        self.desktop.canvas_init(file_path_data=data)
            
    def slice_info_step1_btn3(self, b, output):
        """
        Button on click function clear output

        """
        with output:
            output.clear_output()
            
    def slice_info_step1_btn4(self, b, output, real_path, text):
        """
        Button on click function to display link to open a notebook

        """
        with output:
            output.clear_output()
            if (isinstance(real_path, type(text)) and isinstance(text, list)):
                markdown_text = ''
                if self.src:
                    for i in range(len(text)):
                        markdown_text += f"[{text[i]}]({self.get_relative_path(real_path[i])})" + ' '
                else:
                    for i in range(len(text)):
                        markdown_text += f"[{text[i]}]({self.get_relative_path_with_parent(real_path[i])})" + ' '
                display(Markdown(markdown_text))
        
    def slice_info_step1_btn5(self, b, output, real_path, t):
        """
        Button on click function to display link to open a notebook

        """
        if self.src:
            relative_path = self.get_relative_path_with_parent(real_path)
        else:
            relative_path = self.get_relative_path(real_path)
        with output:
            output.clear_output()
            display(Markdown(f"[{t}]({relative_path})"))
            

    def update_slice_info_checkbox(self, change):
        """
       Observe function to update checkbox values

        """
        self.slice_info_checkbox[change['owner'].description] = change.new
        self.logger.info(self.slice_info_checkbox)
        
    def show_hide_details(self, button, output, text):
        """
        Button on click function to show or hide the output area

        """
        with output:
            output.clear_output(wait=True)
            if button.description == 'Show Details':
                display(widgets.HTML(value=text))
                button.description = 'Hide Details'
            else:
                button.description = 'Show Details'
                output.clear_output()
                
    # This function creates accordion in the run notebooks tab
    def create_accordion(self, my_list, current_state):
        """
        Creates the accordion

        :return: accordion
        :rtype: widgets.Accordion
        """
        accordion_children = []
        wid_list = []
        acc_dict= {'MFLib Instrumentize': False, 'Precision Timing': False, 'Data Transfer Service': False, 'One-Way-Latency': False }

        if 'ELK Stack' in my_list or 'Prometheus' in my_list:
            if 'ELK Stack' in my_list and 'Prometheus' in my_list:
                text = 'You selected both ELK and Prometheus<br>'
                elk_state = self.read_state_requirements_from_file('ELK Stack')
                prom_state = self.read_state_requirements_from_file('Prometheus')
                elk_pre_state = self.read_state_dependencies_from_file(elk_state[0])["required_state"]
                prom_pre_state = self.read_state_dependencies_from_file(prom_state[0])["required_state"]
                prerequisite_state =  self.add_and_unique(elk_pre_state, prom_pre_state)
                text+=f'Prerequisite state: {prerequisite_state}<br>'
                text+=f'Current state: {current_state}<br>'
                state_difference = self.compare_states(prerequisite_state, current_state)
                text+=f'Difference: {state_difference}<br>'
                if len(state_difference)>0:
                    disable_index =0
                    text1 ='Please go back to the previous tab to finish the settings:<br>'
                else:
                    wid_list=[]
                    if ("ELK_INSTRUMENTIZED" in json.loads(current_state)["state"] and "PROMETHEUS_INSTRUMENTIZED" in json.loads(current_state)["state"]):
                        text1 = 'You have already intrumentized both ELK and Promtheus. Go to See Measurements tab.'
                    elif ("ELK_INSTRUMENTIZED" in json.loads(current_state)["state"]):
                        text1 ='State satisfies requirement<br>'
                        text1 +='ELK is instrumentized. You can instrumentize Prometheus using the following notebooks:<br>'
                        prom_nb = self.get_notebook_collection('Prometheus')[0]
                        prom_nb_path = self.get_notebook_path(prom_nb)
                        btn2 = widgets.Button(description='Instrumentize Prometheus', layout=widgets.Layout(width='200px'))
                        output4 = widgets.Output()
                        btn2.on_click(lambda b, p1=prom_nb_path, o1=output4: self.run_notebook_using_btn(b, p1, o1))
                        box= widgets.VBox([btn2, output4])
                        wid_list.append(box)
                    elif ("PROMETHEUS_INSTRUMENTIZED" in json.loads(current_state)["state"]):  
                        text1 ='State satisfies requirement<br>'
                        text1 +='Promtheus is instrumentized. You can instrumentize ELK using the following notebooks:<br>'
                        elk_nb = self.get_notebook_collection('ELK Stack')[0]
                        elk_nb_path = self.get_notebook_path(elk_nb)
                        btn1 = widgets.Button(description='Instrumentize ELK', layout=widgets.Layout(width='200px'))
                        output3 = widgets.Output()
                        btn1.on_click(lambda b, p=elk_nb_path, o=output3: self.run_notebook_using_btn(b, p, o))
                        box= widgets.VBox([btn1, output3])
                        wid_list.append(box)
                    else:
                        text1 ='State satisfies requirement<br>'
                        text1 +='You can instrumentize ELK and Prometheus using the following notebooks:<br>'
                        elk_nb = self.get_notebook_collection('ELK Stack')[0]
                        prom_nb = self.get_notebook_collection('Prometheus')[0]
                        elk_nb_path = self.get_notebook_path(elk_nb)
                        prom_nb_path = self.get_notebook_path(prom_nb)
                        btn1 = widgets.Button(description='Instrumentize ELK', layout=widgets.Layout(width='200px'))
                        btn2 = widgets.Button(description='Instrumentize Prometheus', layout=widgets.Layout(width='200px'))
                        output3 = widgets.Output()
                        output4 = widgets.Output()
                        btn1.on_click(lambda b, p=elk_nb_path, o=output3: self.run_notebook_using_btn(b, p, o))
                        btn2.on_click(lambda b, p1=prom_nb_path, o1=output4: self.run_notebook_using_btn(b, p1, o1))
                        box= widgets.VBox([btn1, output3, btn2, output4])
                        wid_list.append(box)
                    
            elif 'ELK Stack' in my_list:
                wid_list= []
                text = 'You selected ELK Stack<br>'
                elk_state = self.read_state_requirements_from_file('ELK Stack')
                elk_pre_state = self.read_state_dependencies_from_file(elk_state[0])["required_state"]
                prerequisite_state = elk_pre_state
                text+=f'Prerequisite state: {prerequisite_state}<br>'
                text+=f'Current state: {current_state}<br>'
                state_difference = self.compare_states(prerequisite_state, current_state)
                text+=f'Difference: {state_difference}<br>'
                if len(state_difference)>0:
                    disable_index = 0
                    text1 ='Please go back to the previous tab to finish the settings:<br>'
                else:
                    if ("ELK_INSTRUMENTIZED" not in str(current_state)):
                        wid_list=[]
                        text1='State satisfies requirement<br>'
                        text1+='You can instrumentize ELK using the following notebook:<br>'
                        elk_nb = self.get_notebook_collection('ELK Stack')[0]
                        elk_nb_path = self.get_notebook_path(elk_nb)
                        btn1 = widgets.Button(description='Instrumentize ELK', layout=widgets.Layout(width='200px'))
                        output = widgets.Output()
                        btn1.on_click(lambda b: self.run_notebook_using_btn(b, elk_nb_path, output))
                        box= widgets.VBox([btn1, output])
                        wid_list.append(box)
                    else:
                        text1='ELK has been instrumntized<br>'
                        text1+='You can go to "see measurements" tab to view measurement data!<br>'
                        
                
            elif 'Prometheus' in my_list:
                text = 'You selected Prometheus<br>'
                prom_state = self.read_state_requirements_from_file('Prometheus')
                prom_pre_state = self.read_state_dependencies_from_file(prom_state[0])["required_state"]
                prerequisite_state =  prom_pre_state
                text+=f'Prerequisite state: {prerequisite_state}<br>'
                text+=f'Current state: {current_state}<br>'
                state_difference = self.compare_states(prerequisite_state, current_state)
                text+=f'Difference: {state_difference}<br>'
                if len(state_difference)>0:
                    disable_index = 0
                    text1 ='Please go back to the previous tab to finish the settings:<br>'
                else:
                    if ("PROMETHEUS_INSTRUMENTIZED" not in str(current_state)):
                        wid_list=[]
                        text1='Current State satisfies requirements<br>'
                        text1+='You can start instrumentizing Prometheus using the following notebook:<br>'
                        prom_nb = self.get_notebook_collection('Prometheus')[0]
                        prom_nb_path = self.get_notebook_path(prom_nb)
                        btn2 = widgets.Button(description='Instrumentize Prometheus', layout=widgets.Layout(width='200px'))
                        output = widgets.Output()
                        btn2.on_click(lambda b: self.run_notebook_using_btn(b, prom_nb_path, output))
                        box= widgets.VBox([btn2, output])
                        wid_list.append(box)
                    else:
                        text1='Prometheus has been instrumntized<br>'
                        text1+='You can go to "see measurements" tab to view measurement data!<br>'
            show_hide_btn_ins = widgets.Button(description = 'Show Details')
            show_hide_out_ins = widgets.Output()
            show_hide_btn_ins.on_click(lambda b, o=show_hide_out_ins, t=text: self.show_hide_details(b, o, t))
            label_ins = widgets.HTML(value=text1)
            accordion_children.append(widgets.VBox([show_hide_btn_ins]+[show_hide_out_ins]+[label_ins]+[item for item in wid_list]))
            acc_dict['MFLib Instrumentize']=True

        if 'Precision Timing' in my_list:
            wid_list = []
            text = 'You selected Precision Timing<br>'
            prerequisite_state = self.read_state_requirements_from_file('Precision Timing')
            state_difference = self.compare_states(prerequisite_state, current_state)
            text+=f'Prerequisite state: {prerequisite_state}<br>'
            text+=f'Current state: {current_state}<br>'
            text+=f'Difference: {state_difference}<br>'
            
            if (len(state_difference)>0):
                text1 ='Please go back to the previous tab to finish the settings:<br>'
            else:
                wid_list=[]
                text1='Current state satisfies requirements<br>'
                text1+='You can start your Precision Timing Experiments using the following notebooks:<br>'
                nbs = self.get_notebook_collection('Precision Timing')
                #disable_index =0
                for nb in nbs:
                    #disable_index+=1
                    nb_path = self.get_notebook_path(nb)
                    #if (disable_index>1):
                    #    btn = widgets.Button(description='Run Notebook', disabled=True)
                    #else:
                    btn = widgets.Button(description='Run Notebook')
                    #btn = widgets.Button(description='Run Notebook', layout=widgets.Layout(width='200px'))
                    output = widgets.Output()
                    if self.src:
                        relative_path = self.get_relative_path_with_parent(nb_path)
                    else:
                        relative_path = self.get_relative_path(nb_path)
                    with output:
                        output.clear_output()
                        display(Markdown(f"[View {nb} using this link]({relative_path})"))
                    output1 = widgets.Output()
                    config_slice_nb_path = self.path_structure['Config']['CONFIG_SLICE_NOTEBOOK']
                    if (nb_path == config_slice_nb_path):
                        value =self.selected_slice_name.value.replace("'", "").replace("\"", "")
                        btn.on_click(lambda b, p=nb_path, o=output1, v=value: self.run_config_notebook_with_arg(b, p, o, v))
                    else:
                        btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                    #btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                    box = widgets.VBox([widgets.HBox([output, btn]), output1])
                    wid_list.append(box)
                
            show_hide_btn_timing = widgets.Button(description = 'Show Details')
            show_hide_out_timing = widgets.Output()
            show_hide_btn_timing.on_click(lambda b, o=show_hide_out_timing, t=text: self.show_hide_details(b, o, t))
            label_timing = widgets.HTML(value=text1)
            accordion_children.append(widgets.VBox([show_hide_btn_timing]+[show_hide_out_timing]+[label_timing]+[item for item in wid_list]))
            acc_dict['Precision Timing']=True

        if 'Data Transfer service' in my_list:
            wid_list = []
            text = 'You selected Data Transfer service<br>'
            prerequisite_state = self.read_state_requirements_from_file('Data Transfer service')
            state_difference = self.compare_states(prerequisite_state, current_state)
            text+=f'Prerequisite state: {prerequisite_state}<br>'
            text+=f'Current state: {current_state}<br>'
            text+=f'Difference: {state_difference}<br>'
            if (len(state_difference)>0):
                text1 ='Please go back to the previous tab to finish the settings:<br>'
            else:
                wid_list=[]
                text1='Current state satisfies requirements<br>'
                text1+='You can start your Data Transfer service Experiments using the following notebooks:<br>'
                nbs = self.get_notebook_collection('Data Transfer service')
                #disable_index = 0
                for nb in nbs:
                    #disable_index +=1
                    nb_path = self.get_notebook_path(nb)
                    #if (disable_index>1):
                    #    btn = widgets.Button(description='Run Notebook', disabled=True)
                    #else:
                    btn = widgets.Button(description='Run Notebook')
                    #btn = widgets.Button(description='Run Notebook', layout=widgets.Layout(width='200px'))
                    output = widgets.Output()
                    if self.src:
                        relative_path = self.get_relative_path_with_parent(nb_path)
                    else:
                        relative_path = self.get_relative_path(nb_path)
                    with output:
                        output.clear_output()
                        display(Markdown(f"[View {nb} using this link]({relative_path})"))
                    output1 = widgets.Output()
                    config_slice_nb_path = self.path_structure['Config']['CONFIG_SLICE_NOTEBOOK']
                    if (nb_path == config_slice_nb_path):
                        value =self.selected_slice_name.value.replace("'", "").replace("\"", "")
                        btn.on_click(lambda b, p=nb_path, o=output1, v=value: self.run_config_notebook_with_arg(b, p, o, v))
                    else:
                        btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                    #btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                    box = widgets.VBox([widgets.HBox([output, btn]), output1])
                    wid_list.append(box)
            
            show_hide_btn_data = widgets.Button(description = 'Show Details')
            show_hide_out_data = widgets.Output()
            show_hide_btn_data.on_click(lambda b, o=show_hide_out_data, t=text: self.show_hide_details(b, o, t))
            label_data = widgets.HTML(value=text1)
            accordion_children.append(widgets.VBox([show_hide_btn_data]+[show_hide_out_data]+[label_data]+[item for item in wid_list]))  
            acc_dict['Data Transfer Service']=True

        if 'One-Way-Latency (OWL)' in my_list:
            wid_list = []
            text = 'You selected One-Way-Latency (OWL)<br>'
            prerequisite_state = self.read_state_requirements_from_file('One-Way-Latency (OWL)')
            state_difference = self.compare_states(prerequisite_state, current_state)
            text+=f'Prerequisite state: {prerequisite_state}<br>'
            text+=f'Current state: {current_state}<br>'
            text+=f'Difference: {state_difference}<br>'
            
            if (len(state_difference)>0):
                #print ('There is diffrence')
                text1 ='Please go back to the previous tab to finish the settings:<br>'
            else:
                wid_list=[]
                text1='Current state satisfies requirements<br>'
                text1+='You can start your One-Way-Latency (OWL) Experiments using the following notebooks:<br>'
                nbs = self.get_notebook_collection('One-Way-Latency (OWL)')
                #disable_index = 0
                for nb in nbs:
                    nb_path = self.get_notebook_path(nb)
                    #if (disable_index>1):
                    #    btn = widgets.Button(description='Run Notebook', disabled=True)
                    #else:
                    btn = widgets.Button(description='Run Notebook')
                    #btn = widgets.Button(description='Run Notebook', layout=widgets.Layout(width='200px'))
                    output = widgets.Output()
                    if self.src:
                        relative_path = self.get_relative_path_with_parent(nb_path)
                    else:
                        relative_path = self.get_relative_path(nb_path)
                    with output:
                        output.clear_output()
                        display(Markdown(f"[View {nb} using this link]({relative_path})"))
                    output1 = widgets.Output()
                    config_slice_nb_path = self.path_structure['Config']['CONFIG_SLICE_NOTEBOOK']
                    if (nb_path == config_slice_nb_path):
                        value =self.selected_slice_name.value.replace("'", "").replace("\"", "")
                        btn.on_click(lambda b, p=nb_path, o=output1, v=value: self.run_config_notebook_with_arg(b, p, o, v))
                    else:
                        btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                    #btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                    box = widgets.VBox([widgets.HBox([output, btn]), output1])
                    wid_list.append(box)
            #print (wid_list)
            
            show_hide_btn_owl = widgets.Button(description = 'Show Details')
            show_hide_out_owl = widgets.Output()
            show_hide_btn_owl.on_click(lambda b, o=show_hide_out_owl, t=text: self.show_hide_details(b, o, t))
            label_owl = widgets.HTML(value=text1)
            accordion_children.append(widgets.VBox([show_hide_btn_owl]+[show_hide_out_owl]+[label_owl]+[item for item in wid_list]))  
            acc_dict['One-Way-Latency']=True

        accordion = widgets.Accordion(children=accordion_children)
        i=0
        for key, value in acc_dict.items():
            if value is True:
                accordion.set_title(i, key)
                i+=1
        return accordion
    
    
    # This function creates accordion in the run notebooks tab
    def create_accordion_on_mflib_service_tab(self, my_list, current_state):
        """
        Creates the accordion

        :return: accordion
        :rtype: widgets.Accordion
        """
        accordion_children = []
        wid_list = []
        acc_dict= {'MFLib Instrumentize': False, 'Precision Timing': False, 'Data Transfer Service': False, 'One-Way-Latency': False }

        if 'ELK Stack' in my_list or 'Prometheus' in my_list:
            if 'ELK Stack' in my_list and 'Prometheus' in my_list:
                text = 'You selected both ELK and Prometheus<br>'
                elk_state = self.read_state_requirements_from_file('ELK Stack')
                prom_state = self.read_state_requirements_from_file('Prometheus')
                elk_pre_state = self.read_state_dependencies_from_file(elk_state[0])["required_state"]
                prom_pre_state = self.read_state_dependencies_from_file(prom_state[0])["required_state"]
                prerequisite_state =  self.add_and_unique(elk_pre_state, prom_pre_state)
                text+=f'Prerequisite state: {prerequisite_state}<br>'
                text+=f'Current state: {current_state}<br>'
                state_difference = self.compare_states(prerequisite_state, current_state)
                text+=f'Difference: {state_difference}<br>'
                if len(state_difference)>0:
                    disable_index =0
                    text1 ='Run the following notebooks to meet the requirements(Start with the first one):<br>'
                    for s in state_difference:
                        disable_index +=1
                        nb_name = self.read_state_dependencies_from_file(s)["related_notebook"]
                        nb_path = self.get_notebook_path(nb_name)
                        output = widgets.Output()
                        if self.src:
                            relative_path = self.get_relative_path_with_parent(nb_path)
                        else:
                            relative_path = self.get_relative_path(nb_path)
                        with output:
                            output.clear_output()
                            display(Markdown(f"[View {nb_name} using this link]({relative_path})"))
                        output1=widgets.Output()
                        if (disable_index>1):
                            btn = widgets.Button(description='Run Notebook', disabled=True)
                        else:
                            btn = widgets.Button(description='Run Notebook')
                        
                        config_slice_nb_path = self.path_structure['Config']['CONFIG_SLICE_NOTEBOOK']
                        if (nb_path == config_slice_nb_path):
                            value =self.selected_slice_name.value.replace("'", "").replace("\"", "")
                            btn.on_click(lambda b, p=nb_path, o=output1, v=value: self.run_config_notebook_with_arg(b, p, o, v))
                        else:
                            btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                                         
                        box = widgets.VBox([widgets.HBox([output, btn]), output1])
                        wid_list.append(box)
                else:
                    wid_list=[]
                    if ("ELK_INSTRUMENTIZED" in json.loads(current_state)["state"] and "PROMETHEUS_INSTRUMENTIZED" in json.loads(current_state)["state"]):
                        text1 = 'You have already intrumentized both ELK and Promtheus. Go to See_Measurements tab'
                    elif ("ELK_INSTRUMENTIZED" in json.loads(current_state)["state"]):
                        text1 ='State satisfies requirement<br>'
                        text1 +='ELK is instrumentized. You can instrumentize Prometheus in the next tab(Run Experiment)<br>'
                    elif ("PROMETHEUS_INSTRUMENTIZED" in json.loads(current_state)["state"]):  
                        text1 ='State satisfies requirement<br>'
                        text1 +='Promtheus is instrumentized. You can instrumentize ELK in the next tab(Run Experiment)<br>'
                    else:
                        text1 ='State satisfies requirement<br>'
                        text1 +='You can instrumentize ELK and Prometheus in the next tab(Run Experiment)<br>'
                    
            elif 'ELK Stack' in my_list:
                wid_list= []
                text = 'You selected ELK Stack<br>'
                elk_state = self.read_state_requirements_from_file('ELK Stack')
                elk_pre_state = self.read_state_dependencies_from_file(elk_state[0])["required_state"]
                prerequisite_state = elk_pre_state
                text+=f'Prerequisite state: {prerequisite_state}<br>'
                text+=f'Current state: {current_state}<br>'
                state_difference = self.compare_states(prerequisite_state, current_state)
                text+=f'Difference: {state_difference}<br>'
                if len(state_difference)>0:
                    disable_index = 0
                    text1 ='Run the following notebooks to meet the requirements(Start with the first one):<br>'
                    for s in state_difference:
                        disable_index+=1
                        nb_name = self.read_state_dependencies_from_file(s)["related_notebook"]
                        nb_path = self.get_notebook_path(nb_name)
                        output = widgets.Output()
                        if self.src:
                            relative_path = self.get_relative_path_with_parent(nb_path)
                        else:
                            relative_path = self.get_relative_path(nb_path)
                        with output:
                            output.clear_output()
                            display(Markdown(f"[View {nb_name} using this link]({relative_path})"))
                        output1=widgets.Output()
                        if (disable_index>1):
                            btn = widgets.Button(description='Run Notebook', disabled=True)
                        else:
                            btn = widgets.Button(description='Run Notebook')
                        
                        config_slice_nb_path = self.path_structure['Config']['CONFIG_SLICE_NOTEBOOK']
                        if (nb_path == config_slice_nb_path):
                            value =self.selected_slice_name.value.replace("'", "").replace("\"", "")
                            btn.on_click(lambda b, p=nb_path, o=output1, v=value: self.run_config_notebook_with_arg(b, p, o, v))
                        else:
                            btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                        
                        box = widgets.VBox([widgets.HBox([output, btn]), output1])
                        wid_list.append(box)
                else:
                    wid_list=[]
                    text1='State satisfies requirement<br>'
                    text1+='You can instrumentize ELK in the next tab(Run Experiment)<br>'
                    
                
            elif 'Prometheus' in my_list:
                text = 'You selected Prometheus<br>'
                prom_state = self.read_state_requirements_from_file('Prometheus')
                prom_pre_state = self.read_state_dependencies_from_file(prom_state[0])["required_state"]
                prerequisite_state =  prom_pre_state
                text+=f'Prerequisite state: {prerequisite_state}<br>'
                text+=f'Current state: {current_state}<br>'
                state_difference = self.compare_states(prerequisite_state, current_state)
                text+=f'Difference: {state_difference}<br>'
                if len(state_difference)>0:
                    disable_index = 0
                    text1 ='Run the following notebooks to meet the requirements(Start with the first one):<br>'
                    for s in state_difference:
                        disable_index+=1
                        nb_name = self.read_state_dependencies_from_file(s)["related_notebook"]
                        nb_path = self.get_notebook_path(nb_name)
                        output = widgets.Output()
                        if self.src:
                            relative_path = self.get_relative_path_with_parent(nb_path)
                        else:
                            relative_path = self.get_relative_path(nb_path)
                        with output:
                            output.clear_output()
                            display(Markdown(f"[View {nb_name} using this link]({relative_path})"))
                        output1=widgets.Output()
                        if (disable_index>1):
                            btn = widgets.Button(description='Run Notebook', disabled=True)
                        else:
                            btn = widgets.Button(description='Run Notebook')
                            
                        config_slice_nb_path = self.path_structure['Config']['CONFIG_SLICE_NOTEBOOK']
                        if (nb_path == config_slice_nb_path):
                            value =self.selected_slice_name.value.replace("'", "").replace("\"", "")
                            btn.on_click(lambda b, p=nb_path, o=output1, v=value: self.run_config_notebook_with_arg(b, p, o, v))
                        else:
                            btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                        box = widgets.VBox([widgets.HBox([output, btn]), output1])
                        wid_list.append(box)
                else:
                    wid_list=[]
                    text1='Current State satisfies requirements<br>'
                    text1+='You can start instrumentizing Prometheus in the next tab(Run Experiment)<br>'
                    
            show_hide_btn_ins = widgets.Button(description = 'Show Details')
            show_hide_out_ins = widgets.Output()
            show_hide_btn_ins.on_click(lambda b, o=show_hide_out_ins, t=text: self.show_hide_details(b, o, t))
            label_ins = widgets.HTML(value=text1)
            accordion_children.append(widgets.VBox([show_hide_btn_ins]+[show_hide_out_ins]+[label_ins]+[item for item in wid_list]))
            acc_dict['MFLib Instrumentize']=True

        if 'Precision Timing' in my_list:
            wid_list = []
            text = 'You selected Precision Timing<br>'
            prerequisite_state = self.read_state_requirements_from_file('Precision Timing')
            state_difference = self.compare_states(prerequisite_state, current_state)
            text+=f'Prerequisite state: {prerequisite_state}<br>'
            text+=f'Current state: {current_state}<br>'
            text+=f'Difference: {state_difference}<br>'
            
            if (len(state_difference)>0):
                if ('PTP_INSTALLED' in state_difference or 'DOCKER_INSTALLED' in state_difference):
                    text+=f'PTP_INSTALLED or DOCKER_INSTALLED in state difference<br>'
                    if 'ELK Stack' in my_list or 'Prometheus' in my_list:
                        text1='Since you want to instrumentize ELK or Prometheus, we will use MFLib<br>'
                        text1+='Please run the following notebooks:<br>'
                        req = self.read_state_dependencies_from_file('PTP_INSTALLED')[1]["required_state"]
                        new_st_difference = self.compare_states(req, current_state)
                        if len(new_st_difference)>0:
                            disable_index =0
                            for s in new_st_difference:
                                disable_index+=1
                                nb_name = self.read_state_dependencies_from_file(s)["related_notebook"]
                                nb_path = self.get_notebook_path(nb_name)
                                output = widgets.Output()
                                if self.src:
                                    relative_path = self.get_relative_path_with_parent(nb_path)
                                else:
                                    relative_path = self.get_relative_path(nb_path)
                                with output:
                                    output.clear_output()
                                    display(Markdown(f"[View {nb_name} using this link]({relative_path})"))
                                output1=widgets.Output()
                                if (disable_index>1):
                                    btn = widgets.Button(description='Run Notebook', disabled=True)
                                else:
                                    btn = widgets.Button(description='Run Notebook')
                                #btn = widgets.Button(description='Run Notebook')
                                config_slice_nb_path = self.path_structure['Config']['CONFIG_SLICE_NOTEBOOK']
                                if (nb_path == config_slice_nb_path):
                                    value =self.selected_slice_name.value.replace("'", "").replace("\"", "")
                                    btn.on_click(lambda b, p=nb_path, o=output1, v=value: self.run_config_notebook_with_arg(b, p, o, v))
                                else:
                                    btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                                
                                box = widgets.VBox([widgets.HBox([output, btn]), output1])
                                wid_list.append(box)
                    else:
                        wid_list = []
                        text1='Since you have not selected ELK or Prometheus, we will use the install scripts for PTP and Docker<br>'
                        text1+='Please run the following notebooks:<br>'
                        req = self.read_state_dependencies_from_file('PTP_INSTALLED')[0]["required_state"]
                        new_st_difference = self.compare_states(req, current_state)
                        if len(new_st_difference)>0:
                            disable_index =0
                            for s in new_st_difference:
                                disable_index+=1
                                nb_name = self.read_state_dependencies_from_file(s)["related_notebook"]
                                nb_path = self.get_notebook_path(nb_name)
                                output = widgets.Output()
                                if self.src:
                                    relative_path = self.get_relative_path_with_parent(nb_path)
                                else:
                                    relative_path = self.get_relative_path(nb_path)
                                with output:
                                    output.clear_output()
                                    display(Markdown(f"[View {nb_name} using this link]({relative_path})"))
                                output1=widgets.Output()
                                if (disable_index>1):
                                    btn = widgets.Button(description='Run Notebook', disabled=True)
                                else:
                                    btn = widgets.Button(description='Run Notebook')
                                #btn = widgets.Button(description='Run Notebook')
                                config_slice_nb_path = self.path_structure['Config']['CONFIG_SLICE_NOTEBOOK']
                                if (nb_path == config_slice_nb_path):
                                    value =self.selected_slice_name.value.replace("'", "").replace("\"", "")
                                    btn.on_click(lambda b, p=nb_path, o=output1, v=value: self.run_config_notebook_with_arg(b, p, o, v))
                                else:
                                    btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                                #btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                                box = widgets.VBox([widgets.HBox([output, btn]), output1])
                                wid_list.append(box)
                        install_list = ['PTP_INSTALLED', 'DOCKER_INSTALLED']
                        common = [item for item in install_list if item in state_difference]
                        for i in common:
                            nb_name = self.read_state_dependencies_from_file(i)[0]["related_notebook"]
                            nb_path = self.get_notebook_path(nb_name)
                            #print (nb_path)
                            output = widgets.Output()
                            if self.src:
                                relative_path = self.get_relative_path_with_parent(nb_path)
                            else:
                                relative_path = self.get_relative_path(nb_path)
                            with output:
                                output.clear_output()
                                display(Markdown(f"[View {nb_name} using this link]({relative_path})"))
                            output1=widgets.Output()
                            btn = widgets.Button(description='Run Notebook')
                            config_slice_nb_path = self.path_structure['Config']['CONFIG_SLICE_NOTEBOOK']
                            if (nb_path == config_slice_nb_path):
                                value =self.selected_slice_name.value.replace("'", "").replace("\"", "")
                                btn.on_click(lambda b, p=nb_path, o=output1, v=value: self.run_config_notebook_with_arg(b, p, o, v))
                            else:
                                btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                            
                            #btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                            box = widgets.VBox([widgets.HBox([output, btn]), output1])
                            wid_list.append(box)
            else:
                wid_list = []
                text1='Current state satisfies requirements<br>'
                text1+='You can start your Precision Timing Experiments in the next tab(Run Experiments):<br>'
                
            show_hide_btn_timing = widgets.Button(description = 'Show Details')
            show_hide_out_timing = widgets.Output()
            show_hide_btn_timing.on_click(lambda b, o=show_hide_out_timing, t=text: self.show_hide_details(b, o, t))
            label_timing = widgets.HTML(value=text1)
            accordion_children.append(widgets.VBox([show_hide_btn_timing]+[show_hide_out_timing]+[label_timing]+[item for item in wid_list]))
            acc_dict['Precision Timing']=True

        if 'Data Transfer service' in my_list:
            wid_list = []
            text = 'You selected Data Transfer service<br>'
            prerequisite_state = self.read_state_requirements_from_file('Data Transfer service')
            state_difference = self.compare_states(prerequisite_state, current_state)
            text+=f'Prerequisite state: {prerequisite_state}<br>'
            text+=f'Current state: {current_state}<br>'
            text+=f'Difference: {state_difference}<br>'
            if (len(state_difference)>0):
                disable_index = 0
                text1 ='Run the following notebooks to meet the requirements(Start with the first one):<br>'
                for s in state_difference:
                    disable_index+=1
                    nb_name = self.read_state_dependencies_from_file(s)["related_notebook"]
                    nb_path = self.get_notebook_path(nb_name)
                    output = widgets.Output()
                    if self.src:
                        relative_path = self.get_relative_path_with_parent(nb_path)
                    else:
                        relative_path = self.get_relative_path(nb_path)
                    with output:
                        output.clear_output()
                        display(Markdown(f"[View {nb_name} using this link]({relative_path})"))
                    output1=widgets.Output()
                    if (disable_index>1):
                        btn = widgets.Button(description='Run Notebook', disabled=True)
                    else:
                        btn = widgets.Button(description='Run Notebook')
                    config_slice_nb_path = self.path_structure['Config']['CONFIG_SLICE_NOTEBOOK']
                    if (nb_path == config_slice_nb_path):
                        value =self.selected_slice_name.value.replace("'", "").replace("\"", "")
                        btn.on_click(lambda b, p=nb_path, o=output1, v=value: self.run_config_notebook_with_arg(b, p, o, v))
                    else:
                        btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                    #btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                    box = widgets.VBox([widgets.HBox([output, btn]), output1])
                    wid_list.append(box)
            else:
                wid_list = []
                text1='Current state satisfies requirements<br>'
                text1+='You can start your Data Transfer service Experiments in the next tab (Run Experiments):<br>'
                
            show_hide_btn_data = widgets.Button(description = 'Show Details')
            show_hide_out_data = widgets.Output()
            show_hide_btn_data.on_click(lambda b, o=show_hide_out_data, t=text: self.show_hide_details(b, o, t))
            label_data = widgets.HTML(value=text1)
            accordion_children.append(widgets.VBox([show_hide_btn_data]+[show_hide_out_data]+[label_data]+[item for item in wid_list]))  
            acc_dict['Data Transfer Service']=True

        if 'One-Way-Latency (OWL)' in my_list:
            wid_list = []
            text = 'You selected One-Way-Latency (OWL)<br>'
            prerequisite_state = self.read_state_requirements_from_file('One-Way-Latency (OWL)')
            state_difference = self.compare_states(prerequisite_state, current_state)
            text+=f'Prerequisite state: {prerequisite_state}<br>'
            text+=f'Current state: {current_state}<br>'
            text+=f'Difference: {state_difference}<br>'
            
            if (len(state_difference)>0):
                #print ('There is diffrence')
                if ('PTP_INSTALLED' in state_difference or 'DOCKER_INSTALLED' in state_difference):
                    text+=f'PTP_INSTALLED or DOCKER_INSTALLED in state difference<br>'
                    if 'ELK Stack' in my_list or 'Prometheus' in my_list:
                        text1='Since you want to instrumentize ELK or Prometheus, we will use MFLib which will install PTP and docker for you<br>'
                        text1+='Please run the following notebooks:<br>'
                        req = self.read_state_dependencies_from_file('PTP_INSTALLED')[1]["required_state"]
                        #print (req)
                        new_st_difference = self.compare_states(req, current_state)
                        #print (new_st_difference)
                        if len(new_st_difference)>0:
                            disable_index = 0
                            for s in new_st_difference:
                                disable_index +=1
                                nb_name = self.read_state_dependencies_from_file(s)["related_notebook"]
                                nb_path = self.get_notebook_path(nb_name)
                                output = widgets.Output()
                                if self.src:
                                    relative_path = self.get_relative_path_with_parent(nb_path)
                                else:
                                    relative_path = self.get_relative_path(nb_path)
                                with output:
                                    output.clear_output()
                                    display(Markdown(f"[View {nb_name} using this link]({relative_path})"))
                                output1=widgets.Output()
                                if (disable_index>1):
                                    btn = widgets.Button(description='Run Notebook', disabled=True)
                                else:
                                    btn = widgets.Button(description='Run Notebook')
                                #btn = widgets.Button(description='Run Notebook')
                                config_slice_nb_path = self.path_structure['Config']['CONFIG_SLICE_NOTEBOOK']
                                if (nb_path == config_slice_nb_path):
                                    value =self.selected_slice_name.value.replace("'", "").replace("\"", "")
                                    btn.on_click(lambda b, p=nb_path, o=output1, v=value: self.run_config_notebook_with_arg(b, p, o, v))
                                else:
                                    btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                                #btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                                box = widgets.VBox([widgets.HBox([output, btn]), output1])
                                wid_list.append(box)
                    else:
                        wid_list=[]
                        text1='Since you have not selected ELK or Prometheus, we will use the install scripts for PTP and Docker<br>'
                        text1+='Please run the following notebooks:<br>'
                        req = self.read_state_dependencies_from_file('PTP_INSTALLED')[0]["required_state"]
                        new_st_difference = self.compare_states(req, current_state)
                        if len(new_st_difference)>0:
                            disable_index = 0
                            for s in new_st_difference:
                                disable_index +=1
                                nb_name = self.read_state_dependencies_from_file(s)["related_notebook"]
                                nb_path = self.get_notebook_path(nb_name)
                                output = widgets.Output()
                                if self.src:
                                    relative_path = self.get_relative_path_with_parent(nb_path)
                                else:
                                    relative_path = self.get_relative_path(nb_path)
                                with output:
                                    output.clear_output()
                                    display(Markdown(f"[View {nb_name} using this link]({relative_path})"))
                                output1=widgets.Output()
                                if (disable_index>1):
                                    btn = widgets.Button(description='Run Notebook', disabled=True)
                                else:
                                    btn = widgets.Button(description='Run Notebook')
                                #btn = widgets.Button(description='Run Notebook')
                                config_slice_nb_path = self.path_structure['Config']['CONFIG_SLICE_NOTEBOOK']
                                if (nb_path == config_slice_nb_path):
                                    value =self.selected_slice_name.value.replace("'", "").replace("\"", "")
                                    btn.on_click(lambda b, p=nb_path, o=output1, v=value: self.run_config_notebook_with_arg(b, p, o, v))
                                else:
                                    btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                                #btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                                box = widgets.VBox([widgets.HBox([output, btn]), output1])
                                wid_list.append(box)
                        install_list = ['PTP_INSTALLED', 'DOCKER_INSTALLED']
                        common = [item for item in install_list if item in state_difference]
                        disable_index = 0
                        for i in common:
                            disable_index +=1
                            nb_name = self.read_state_dependencies_from_file(i)[0]["related_notebook"]
                            nb_path = self.get_notebook_path(nb_name)
                            #print (nb_path)
                            output = widgets.Output()
                            if self.src:
                                relative_path = self.get_relative_path_with_parent(nb_path)
                            else:
                                relative_path = self.get_relative_path(nb_path)
                            with output:
                                output.clear_output()
                                display(Markdown(f"[View {nb_name} using this link]({relative_path})"))
                            output1=widgets.Output()
                            if (disable_index>1):
                                btn = widgets.Button(description='Run Notebook', disabled=True)
                            else:
                                btn = widgets.Button(description='Run Notebook')
                            #btn = widgets.Button(description='Run Notebook')
                            btn.on_click(lambda b, p=nb_path, o=output1: self.run_notebook_using_btn(b, p, o))
                            box = widgets.VBox([widgets.HBox([output, btn]), output1])
                            wid_list.append(box)
            else:
                wid_list = []
                text1='Current state satisfies requirements<br>'
                text1+='You can start your One-Way-Latency (OWL) Experiments in the next tab (Run Experiments):<br>'
            
            show_hide_btn_owl = widgets.Button(description = 'Show Details')
            show_hide_out_owl = widgets.Output()
            show_hide_btn_owl.on_click(lambda b, o=show_hide_out_owl, t=text: self.show_hide_details(b, o, t))
            label_owl = widgets.HTML(value=text1)
            accordion_children.append(widgets.VBox([show_hide_btn_owl]+[show_hide_out_owl]+[label_owl]+[item for item in wid_list]))  
            acc_dict['One-Way-Latency']=True

        accordion = widgets.Accordion(children=accordion_children)
        i=0
        for key, value in acc_dict.items():
            if value is True:
                accordion.set_title(i, key)
                i+=1
        return accordion
    
    
    
    
    def update_mflib_service_widget(self, change):
        """
        Updates the mflib notebook widget

        """
        #print ('start update notebook wid:' + str(datetime.datetime.now()))
        accordion=None
        true_keys=None
        if isinstance(change['owner'], widgets.Checkbox):
            self.mflib_service_checkbox[change['owner'].description] = change.new
        if all(value is False for value in self.mflib_service_checkbox.values()):
            text = 'You have not selected any MFLib services<br>'
        else:
            # Print keys with True values
            true_keys = [key for key, value in self.mflib_service_checkbox.items() if value is True]
            #self.logger.info(true_keys)
            text = f"You have selected the following MFLib services: <br>{true_keys}"
        if true_keys and self.selected_slice_state.value!='none':
            accordion = self.create_accordion_on_mflib_service_tab(true_keys, self.selected_slice_state.value) 
        
        children = self.mflib_service_tab_widget.children
        if accordion:
            new_children = (children[0], children[1], accordion, children[3])
            
        else:
            new_children = (children[0], children[1], widgets.Accordion(), children[3])
        
        self.mflib_service_tab_widget.children = new_children

    
    
    
    
    
    
    
    
    def update_mflib_notebooks_widget(self, change):
        """
        Updates the mflib notebook widget

        """
        #print ('start update notebook wid:' + str(datetime.datetime.now()))
        accordion=None
        true_keys=None
        if isinstance(change['owner'], widgets.Checkbox):
            self.mflib_service_checkbox[change['owner'].description] = change.new
        if all(value is False for value in self.mflib_service_checkbox.values()):
            text = 'You have not selected any MFLib services<br>'
        else:
            # Print keys with True values
            true_keys = [key for key, value in self.mflib_service_checkbox.items() if value is True]
            #self.logger.info(true_keys)
            text = f"You have selected the following MFLib services: <br>{true_keys}"
        separator = widgets.HTML("<hr style='height:2px;border-width:0;color:gray;background-color:gray;margin-top:5px;margin-bottom:10px;'/>")
        box2_title = widgets.HTML("<h2 style='color: mediumpurple;'>MFLib Experiments</h2>")
        label = widgets.HTML(value=text)
        if true_keys and self.selected_slice_state.value!='none':
            accordion = self.create_accordion(true_keys, self.selected_slice_state.value) 
        children = self.run_notebooks_tab_widget.children
        if accordion:
            new_child = widgets.VBox([children[2].children[0], widgets.VBox([label, accordion]), children[2].children[2]])
        else:
            new_child = widgets.VBox([children[2].children[0], label, children[2].children[2]])
        if (len(children)==4):
            new_children = (children[0], children[1], new_child, children[3])
        elif (len(children)==5):
            new_children = (children[0], children[1], new_child, children[3], children[4])
        self.run_notebooks_tab_widget.children = new_children
        
        if isinstance(change['owner'], widgets.Text):
            if (self.selected_slice_state.value!='none'):
                s = json.loads(self.selected_slice_state.value)
                if ("SLICE_SUBMITTED" in s["state"]):
                    n_children = self.run_notebooks_tab_widget.children
                    box3_title = widgets.HTML("<h2 style='color: darkgreen;'>Log in to nodes</h2>")
                    box3_dropdown1 = widgets.Dropdown(
                        options= [n.get_name() for n in self.slice_loader.get_nodes()],
                        description='Node:',
                        style={'description_width': 'initial'},
                        layout={'width': '400px'}
                    )
                    box3_open_terminal_btn = widgets.Button(description='Open Terminal')
                    box3_op1 = widgets.Output()
                    pa = self.path_structure['Terminal']['OPEN_TM_NB_DIR']
                    box3_open_terminal_btn.on_click(lambda b, p=pa, o=box3_op1: self.open_terminal(b,p,o))
                
                    new_wid = widgets.VBox([box3_title, widgets.HBox([box3_dropdown1,box3_open_terminal_btn]),box3_op1])
                    new_c = (n_children[0], n_children[1], n_children[2], n_children[3], new_wid)
                    self.run_notebooks_tab_widget.children = new_c
                else:
                    n_children = self.run_notebooks_tab_widget.children
                    new_c = (n_children[0], n_children[1], n_children[2], n_children[3])
                    self.run_notebooks_tab_widget.children = new_c
            else:
                n_children = self.run_notebooks_tab_widget.children
                new_c = (n_children[0], n_children[1], n_children[2], n_children[3])
                self.run_notebooks_tab_widget.children = new_c
        #print ('end update notebook wid:' + str(datetime.datetime.now()))
                
            
            
    def read_variables_from_load_variable_file(self):
        """
        Reads the variables names and values from the file

        """
        try:
            with open(self.path_structure['Setup']['VARIABLES_FILE'], 'r') as file:
                #print (f"reading avriables from {self.path_structure['Setup']['VARIABLES_FILE']}")
                for line in file:
                    if 'slice_name' in line:
                        self.slice_name_variable = line.split("=")[1].strip()
                    elif 'notebook_name' in line:
                        self.notebook_name_variable = line.split("=")[1].strip()
        except FileNotFoundError:
            self.logger.error(f"Error: File not found - {self.path_structure['Setup']['VARIABLES_FILE']}")
        except Exception as e:
            self.logger.error(f'Error: {e}')
        
    
    def write_selected_slice_name(self, name):
        """
        Write selected slice name to file

        """
        name_without_quotes = name.replace("'", "")
        content = f'selected_slice = \'{name_without_quotes}\'\n'
        try:
            with open(self.path_structure['Slice']['SELECTED_SLICE'], 'w') as file:
                self.logger.info(f"writing {name} to {self.path_structure['Slice']['SELECTED_SLICE']}")
                file.write(content)
        except FileNotFoundError:
            self.logger.error(f"Error: File not found - {self.path_structure['Slice']['SELECTED_SLICE']}")
        except Exception as e:
            self.logger.error(f'Error: {e}')
            
            
            
    def write_slice_name_to_file(self):
        with open(self.path_structure['Setup']['VARIABLES_FILE'], 'r') as file:
            lines = file.readlines()
        
        for i, line in enumerate(lines):
            if 'slice_name' in line:
                # Replace the value with the new one
                n = self.selected_slice_name.value.replace("'", "").replace("\"", "")
                lines[i] = f"slice_name = \'{n}\'\n"
                break
        print (f'writing {n} to the load variable file')
        with open(self.path_structure['Setup']['VARIABLES_FILE'], 'w') as file:
            file.writelines(lines)
    
    def get_submitted_slice_names(self):
        """
        Get list of submitted slice names

        :return: slice name list
        :rtype: List
        """
        slice_names = []
        try:
            slices = self.fablib.get_slices()
            for s in slices:
                slice_names.append(s.slice_name)
            return slice_names
        except Exception as e:
            self.logger.error(f"Exception: {e}")
        
    
    def slice_by_modify_notebooks(self, b, output):
        """
        Button on click function to select slice from notebooks

        """
        # Set selected slice name read from load topology and write to selected slice
        with output:
            output.clear_output()
            self.slice_submitted.value = False
            self.fim_state = 'none'
            self.selected_slice_state.value='none'
            self.slice_loader = None
            #self.node_ssh_cmds = None
            self.read_variables_from_load_variable_file()
            name= self.slice_name_variable.replace("'", "").replace("\"", "")
            if (name in self.fabric_slice_names):
                html_text = f'<span style="color: red;">Slice {name} has been submitted. Please change your slice_name value in the first file above(load_variables.py)</span>'
                self.slice_submitted.value = False
                self.selected_slice_name.value = 'none'
                self.fim_state = 'none'
                self.selected_slice_state.value = 'none'
                display(widgets.HTML(value = html_text))   
            elif name=='':
                self.slice_submitted.value = False
                html_text = f'<span style="color: red;">Slice name is empty. Please change your slice_name value in the first file above(load_variables.py)</span>'
                self.selected_slice_name.value='none'
                self.fim_state = 'none'
                self.selected_slice_state.value = 'none'
                display(widgets.HTML(value = html_text))   
            else:
                html_text = f'<span style="color: green;">Selected slice {name}. You can use the Submit slice button below to submit your slice.</span>'
                self.set_selected_slice_name()
                # set slice not submitted
                self.slice_submitted.value = False
                self.fim_state = 'none'
                self.selected_slice_state.value = 'none'
                self.backup_slice_info(self.path_structure['Slice']['SLICE_INFO_DIR'], self.selected_slice_name.value.replace("'", "").replace("\"", ""), 'define_slice.ipynb', 'topology_variables.ipynb')
                display(widgets.HTML(value = html_text))
                for widget in self.slice_info_tab_widget.children[1].children:
                    widget.layout.visibility = 'visible'
                    widget.layout.display = ''
                
                
    def load_saved_slice(self, b, output):
        """
        Button on click function to load saved slice

        """
        # Set selected slice name read from load topology and write to selected slice
        with output:
            output.clear_output()
            self.slice_submitted.value = False
            self.fim_state = 'none'
            self.selected_slice_state.value = 'none'
            dropdown_value = self.slice_info_tab_widget.children[0].children[6].children[1].children[0].value
            if dropdown_value:
                name = dropdown_value.replace("'", "").replace("\"", "")
                html_text = f'<span style="color: green;">Selected slice {name}</span>'
                self.selected_slice_name.value = name
                self.set_selected_slice_name_using_arg(self.selected_slice_name.value)
                if (name in self.fabric_slice_names):
                    st = self.get_slice_state(slice_name=name)
                    if (st == "StableOK"):
                        self.slice_loader = self.fablib.get_slice(name=name)
                        #self.node_ssh_cmds = self.get_ssh_cmd_from_slice(self.slice_loader.get_nodes())
                        html_text1 = f'<span style="color: green;">The selected slice {name} has been submitted. Go to next tab to configure it.</span>'
                        self.slice_submitted.value = True
                        self.fim_state = state.get_state_in_fim(name)
                        self.selected_slice_state.value = self.fim_state
                        for widget in self.slice_info_tab_widget.children[1].children:
                            widget.layout.visibility = 'hidden'
                            widget.layout.display = 'none'
                        os.environ['SELECTED_SLICE'] = name
                    elif (st == "Configuring"):
                        html_text1 = f'<span style="color: red;">The slice {name} state is {st}. Wait for it to become StableOK</span>'
                    else:
                        html_text1 = f'<span style="color: red;">The slice {name} state is {st}. You want to make sure the state is StableOK to continue your experiments</span>'
                else:
                    self.slice_submitted.value = False
                    self.slice_loader = None
                    #self.node_ssh_cmds = None
                    self.fim_state = 'none'
                    self.selected_slice_state.value = 'none'
                    html_text1 = f'<span style="color: red;">The selected slice {name} has not been submitted. Use the button below to submit it.</span>'
                    # function to copy the files from saved slice folder to slice_info 
                    self.copy_files_back(dropdown_value.replace("'", "").replace("\"", ""), 'define_slice.ipynb', 'topology_variables.ipynb', self.path_structure['Slice']['SLICE_INFO_DIR'])
                    self.write_slice_name_to_file()
                    for widget in self.slice_info_tab_widget.children[1].children:
                        widget.layout.visibility = 'visible'
                        widget.layout.display = ''
                    os.environ['SELECTED_SLICE'] = name
                display(widgets.HTML(value = html_text)) 
                display(widgets.HTML(value = html_text1)) 
            else:
                html_text2 = f'<span style="color: red;">Please select the slice</span>'
                display(widgets.HTML(value = html_text2)) 
                
                
        
    def update_slice_loaded_or_save_value(self, checkbox, new_value):
        """
        Call back function to update the value of slice_loaded and slice_saved

        """
        #slice_names = self.get_submitted_slice_names()
        if checkbox == 'loaded submitted slice':
            self.slice_loaded.value = new_value
            self.slice_loaded.observe(self.on_load_change, names='value')
            if (self.slice_loaded.value is True):
                self.selected_slice_name.value = self.desktop.loaded_slice_name
                self.slice_submitted.value = True
                self.logger.info(f'loaded slice {self.selected_slice_name.value} from gui')
                n = self.selected_slice_name.value.replace("'", "").replace("\"", "")
                self.fim_state = state.get_state_in_fim(n)
                self.selected_slice_state.value = self.fim_state
                if ('state' in self.selected_slice_state.value and 'slice_name' in self.selected_slice_state.value):
                    state.set_state_local(json.loads(self.selected_slice_state.value))
                else:
                    self.logger.info('The loaded slice does not have states set by the Experiment Framework')
                    self.logger.info("Setting default state to ['SLICE_DEFINED', 'SLICE_SUBMITTED']")
                    data = {'slice_name': self.selected_slice_name.value, 'state': ['SLICE_DEFINED', 'SLICE_SUBMITTED']}
                    state.set_state_local(data)
            else:
                self.logger.info('slice loaded: False')
                self.slice_submitted.value = False
                self.selected_slice_name.value = 'none'
                self.fim_state = 'none'
                self.selected_slice_state.value='none'
                
        elif checkbox == 'saved unsubmitted slice':
            if new_value is True:
                self.slice_submitted.value = False
                self.selected_slice_name.value = self.desktop.saved_new_slice_name
            else:
                if (self.slice_loaded.value is True):
                    self.logger.info('slice loaded: True')
                else:
                    self.slice_submitted.value = False
                    self.selected_slice_name.value = 'none'
                
        self.logger.info('selected '+self.selected_slice_name.value)
        self.logger.info(f'slice_submitted: {self.slice_submitted.value}')
                
            
    def disable_widgets(self, container):
        for child in container.children:
            if isinstance(child, widgets.Box):
                disable_widgets(child)
            else:
                child.disabled = True
                
    def enable_widgets(self, container):
        for child in container.children:
            if isinstance(child, widgets.Box):
                enable_widgets(child)
            else:
                child.disabled = False
                
    def run_notebook(self, notebook_path):
        """
        Run a notebook without using a button
        
        """
        ori_cwd = os.getcwd()
        # Get the directory of the notebook
        notebook_dir = os.path.dirname(notebook_path)

        # change working dir
        self.logger.info('Changing working dir to:')
        get_ipython().run_line_magic('cd', notebook_dir)

        # execute the notebook
        get_ipython().run_line_magic('run', notebook_path)

        # Reset the current working directory back to its original value
        get_ipython().run_line_magic('cd', ori_cwd)
        
        
    
    def run_config_notebook_with_arg(self, b, notebook_path, output, value):
        """
        Button on click function to run a notebook and update state

        """
        ori_cwd = os.getcwd()
        with output:
            output.clear_output()
            self.logger.info(f"Running {notebook_path}")
            # Get the directory of the notebook
            try:
                os.environ['SELECTED_SLICE'] = value
                notebook_dir = os.path.dirname(notebook_path)

                # change working dir
                self.logger.info('Changing working dir to:')
                get_ipython().run_line_magic('cd', notebook_dir)

                # execute the notbook
                get_ipython().run_line_magic('run', notebook_path)

                # Reset the current working directory back to its original value
                get_ipython().run_line_magic('cd', ori_cwd)
                #slice_names = self.get_submitted_slice_names()
                n = self.selected_slice_name.value.replace("'", "").replace("\"", "")
                if (n in self.fabric_slice_names):
                    self.slice_submitted.value = True
                    self.fim_state = state.get_state_in_fim(n)
                    self.selected_slice_state.value = self.fim_state
                else:
                    self.logger.info(f'{n} not found in the submitted slices')
            except Exception as e:
                print(f"Exception: {e}")
    
    
    
    
    
        
    def run_notebook_using_btn(self, b, notebook_path, output):
        """
        Button on click function to run a notebook and update state

        """
        ori_cwd = os.getcwd()
        with output:
            output.clear_output()
            self.logger.info(f"Running {notebook_path}")
            # Get the directory of the notebook
            try:
                notebook_dir = os.path.dirname(notebook_path)

                # change working dir
                self.logger.info('Changing working dir to:')
                get_ipython().run_line_magic('cd', notebook_dir)

                # execute the notbook
                get_ipython().run_line_magic('run', notebook_path)

                # Reset the current working directory back to its original value
                get_ipython().run_line_magic('cd', ori_cwd)
                #slice_names = self.get_submitted_slice_names()
                n = self.selected_slice_name.value.replace("'", "").replace("\"", "")
                if (n in self.fabric_slice_names):
                    self.slice_submitted.value = True
                    self.fim_state = state.get_state_in_fim(n)
                    self.selected_slice_state.value = self.fim_state
                else:
                    self.logger.info(f'{n} not found in the submitted slices')
            except Exception as e:
                print(f"Exception: {e}")
            
    def run_notebook_using_btn_no_state(self, b, notebook_path, output):
        """
        Button on click function to run a notebook without updating the state

        """
        ori_cwd = os.getcwd()
        with output:
            output.clear_output()
            self.logger.info(f"Running {notebook_path}")
            # Get the directory of the notebook
            try:
                notebook_dir = os.path.dirname(notebook_path)
                # change working dir
                self.logger.info('Changing working dir to:')
                get_ipython().run_line_magic('cd', notebook_dir)

                # execute the notbook
                get_ipython().run_line_magic('run', notebook_path)

                # Reset the current working directory back to its original value
                get_ipython().run_line_magic('cd', ori_cwd)
            except Exception as e:
                print(f"Exception: {e}")
            
            
    def submit_slice_using_btn(self, b, output):
        """
        Button on click function to submit a slice
        """
        ori_cwd = os.getcwd()
        with output:
            output.clear_output()
            if self.slice_info_checkbox['post boot script']:
                notebook_path = self.path_structure['Slice']['SUBMIT_SLICE_POSTBOOT_NOTEBOOK']
                self.logger.info(f"Running {notebook_path}")
            else:
                notebook_path = self.path_structure['Slice']['SUBMIT_SLICE_NOTEBOOK']
                self.logger.info(f"Running {notebook_path}")
            
            self.set_selected_slice_name()
            # Get the directory of the notebook
            notebook_dir = os.path.dirname(notebook_path)
            
            self.fabric_slice_names = self.get_submitted_slice_names()
            n = self.selected_slice_name.value.replace("'", "").replace("\"", "")
            if (n in self.fabric_slice_names):
                html = f'<span style="color: red; font-size: 12px;">Slice {n} is already submitted; change the slice name</span>'
                display(HTML(html))
            else:
                try:  
                    # change working dir
                    self.logger.info('Changing working dir to:')
                    get_ipython().run_line_magic('cd', notebook_dir)

                    # execute the notbook
                    get_ipython().run_line_magic('run', notebook_path) 
                
                    # Reset the current working directory back to its original value
                    get_ipython().run_line_magic('cd', ori_cwd)
                
                    self.fabric_slice_names = self.get_submitted_slice_names()
                    n = self.selected_slice_name.value.replace("'", "").replace("\"", "")
                    if (n in self.fabric_slice_names):
                        st = self.get_slice_state(slice_name=n)
                        if (st == "StableOK"):
                            self.slice_loader = self.fablib.get_slice(name=n)
                            #self.node_ssh_cmds = self.get_ssh_cmd_from_slice(self.slice_loader.get_nodes())
                            self.slice_submitted.value = True
                            self.fim_state = state.get_state_in_fim(n)
                            self.selected_slice_state.value = self.fim_state
                            self.logger.info(f'You can go to the next tab to configure your slice.')
                    else:
                        self.logger.info(f'{n} not found in the submitted slices')
                    self.backup_slice_info(self.path_structure['Slice']['SLICE_INFO_DIR'], n, 'define_slice.ipynb', 'topology_variables.ipynb')
                except Exception as e:
                    print(f"Exception: {e}")
            
    
    def set_selected_slice_name(self):
        """
        Writes the selected slice name to file

        """
        try:
            with open(self.path_structure['Setup']['VARIABLES_FILE'], 'r') as file:
                lines = file.readlines()
            for l in lines:
                if ('slice_name' in l):
                    s_value = l.split('=')[1].strip()
            if not s_value:
                self.logger.error("slice_name not found")
                return
            else:
                self.logger.info(f'Setting the selected slice name to {s_value}')
                self.selected_slice_name.value = s_value
                self.write_selected_slice_name(self.selected_slice_name.value)
        except FileNotFoundError:
            self.logger.error(f"Error: File not found - {self.path_structure['Setup']['VARIABLES_FILE']}")
        except Exception as e:
            self.logger.error(f'Error: {e}')
            
    def set_selected_slice_name_using_arg(self, name):
        """
        Writes the selected slice name to file

        """
        try:
            self.logger.info(f'Setting the selected slice name to {name}')
            #self.selected_slice_name.value = name
            self.write_selected_slice_name(self.selected_slice_name.value)
        except Exception as e:
            self.logger.error(f'Error: {e}')
                    
    
    def generate_post_boot_code(self):
        """
        Writes the postboot code in post_boot.ipynb

        """
        #read the second code cell in define slice notebook
        define_slice_notebook_path = self.path_structure['Slice']['DEFINE_SLICE_NOTEBOOK']
        with open(define_slice_notebook_path, 'r', encoding='utf-8') as notebook_file:
            notebook_content = nbformat.read(notebook_file, as_version=4)
        code_cells = []
        for cell in notebook_content['cells']:
            if cell['cell_type'] == 'code':
                code_cells.append(cell['source'])
        code = code_cells[1]
        lines = code.split('\n')
        new_lines = []
        # Iterate over the lines and modify the code
        for i, line in enumerate(lines):
            if "add_node(" in line:
                # Extract the object name (e.g., node1, node2, etc.)
                object_name = line.split('=')[0].strip()
                new_lines.append(f"    {object_name}.add_post_boot_upload_file('post_boot.sh')")
                new_lines.append(f"    {object_name}.add_post_boot_execute('chmod +x post_boot.sh && ./post_boot.sh')")
        new_lines = ['try:']+new_lines+['except Exception as e:', '    print(f"Exception: {e}")']
        post_boot_notebook_path = self.path_structure['Slice']['POST_BOOT_NOTEBOOK']
        with open(post_boot_notebook_path, 'r', encoding='utf-8') as nb_file:
            notebook = nbformat.read(nb_file, as_version=4)

        # Create a new code cell at the end of the notebook
        new_code_cell = nbformat.v4.new_code_cell(source='\n'.join(new_lines))
        self.logger.info("The generated code is:")
        self.logger.info(new_code_cell['source'])
        notebook['cells'].append(new_code_cell)
        
        self.logger.info(f"Writing the new code to {post_boot_notebook_path}")
        # Write the modified notebook back to the file
        with open(post_boot_notebook_path, 'w', encoding='utf-8') as nb_file:
            nbformat.write(notebook, nb_file)
        
        
        
    
    def add_slice_options(self, b, output):
        """
        Updates the option widget

        """
        with output:
            output.clear_output()
            #Check the values of the checkbox
            if all(value is False for value in self.slice_info_checkbox.values()):
                self.logger.warning("You have not selected any features")
            else:
                true_keys = [key for key, value in self.slice_info_checkbox.items() if value is True]
                for k in true_keys:
                    if (k == 'random_sites'):
                        path = self.path_structure['Slice']['RANDOM_SITES_NOTEBOOK']
                        self.logger.info(f"Running {path}")
                        self.run_notebook(path)
                        self.logger.info('\n\n')
                    elif (k == 'random_ptp_sites'):
                        path = self.path_structure['Slice']['RANDOM_PTP_SITES_NOTEBOOK']
                        self.logger.info(f"Running {path}")
                        self.run_notebook(path)
                        self.logger.info('\n\n')
                    elif (k == 'generate_graphml'):
                        path = self.path_structure['Slice']['GENERATE_GRAPHML_NOTEBOOK']
                        self.logger.info(f"Running {path}")
                        self.run_notebook(path)
                        self.logger.info('\n\n')
                    elif (k == 'post_boot_script'):
                        self.generate_post_boot_code()
                        self.logger.info('\n\n')
    
    
    def next_tab(self, b):
        """
        Goes to the next tab

        """
        # Get the current selected tab index
        current_index = self.main_tab.selected_index
    
        # next index
        next_index = (current_index + 1) % len(self.main_tab.children)
    
        # Set the next tab as the selected tab
        self.main_tab.selected_index = next_index
    
    
    def update_state_info_widget(self, change):
        """
        Updates the state info tab

        """
        #print ('start update state wid:' + str(datetime.datetime.now()))
        if (change['owner'].description == 'ssubmitted' or change['owner'].description == 'sname'):
            if self.selected_slice_name.value == 'none':
                text = 'You have not selected any slice'
            else:
                text = f'Selected slice: {self.selected_slice_name.value}<br>'
            if (self.slice_submitted.value is True):
                if (self.selected_slice_name.value != 'none'):
                    #text+= 'State: '+str(state.get_state_in_fim(self.selected_slice_name.value))+'<br>'
                    pass
            else:
                if (self.selected_slice_name.value != 'none'):
                    text= "The selected slice has not been submitted. Please submit and configure your slice.<br>"
                else:
                    text = 'You have not selected any slice'
        elif (change['owner'].description == 'state'):        
            if self.selected_slice_name.value == 'none':
                text = 'You have not selected any slice'
            else:
                text = f'Selected slice: {self.selected_slice_name.value}<br>'
                if (self.slice_submitted.value is True):
                    if (self.selected_slice_name.value != 'none'):
                        #text+= 'State: '+str(state.get_state_in_fim(self.selected_slice_name.value))+'<br>'
                        text+= 'State: '+str(self.fim_state)+'<br>'
                        
                else:
                    if (self.selected_slice_name.value != 'none'):
                        text="The selected slice has not been submitted. Please submit and configure your slice.<br>"
                    else:
                        text = 'You have not selected any slice'
                
        label = widgets.HTML(value=text)
        children = self.slice_state_tab_widget.children
        new_children = (children[0], label, children[2])
        self.slice_state_tab_widget.children = new_children
        #print ('end update state wid:' + str(datetime.datetime.now()))
    
    
    
    
    def update_config_widget(self, change):
        """
        Updates the config tab

        """
        #print ('start update config wid:' + str(datetime.datetime.now()))
        to_hide = False
        if (change['owner'].description == 'ssubmitted' or change['owner'].description == 'sname'):
            #slice_names = self.get_submitted_slice_names()
            if self.selected_slice_name.value == 'none':
                text = 'You have not selected any slice'
                to_hide = True
            else:
                text = f'Selected slice: {self.selected_slice_name.value}<br>'
            if (self.slice_submitted.value is True):
                if (self.selected_slice_name.value != 'none'):
                    pass
                    #n = self.selected_slice_name.value.replace("'", "").replace("\"", "")
                    #if (n in self.fabric_slice_names):
                    #    s_state = state.get_state_in_fim(n)
                    #    text+= 'State: '+str(s_state)+'<br>'          
            else:
                if (self.selected_slice_name.value != 'none'):
                    text="The selected slice has not been submitted. Please submit and configure your slice.<br>"
                    to_hide = True
                else:
                    text = 'You have not selected any slice'
                    to_hide = True
        elif (change['owner'].description == 'state'):
            if self.selected_slice_name.value == 'none':
                text = 'You have not selected any slice'
                to_hide = True
            else:
                text = f'Selected slice: {self.selected_slice_name.value}<br>'
                if (self.slice_submitted.value is True):
                    if (self.selected_slice_name.value != 'none'):
                        n = self.selected_slice_name.value.replace("'", "").replace("\"", "")
                        if (n in self.fabric_slice_names):
                            #s_state = state.get_state_in_fim(n)
                            s_state = self.fim_state
                            text+= 'State: '+str(s_state)+'<br>' 
                            if 'SLICE_CONFIGURED' in json.loads(s_state)["state"]:
                                text+= 'You have configured this slice. You can start your experiments in the tabs on the right side!' +'<br>'
                                to_hide = True
                            elif 'SLICE_SUBMITTED' in json.loads(s_state)["state"]:
                                text+= 'You have submitted this slice. Please configure it.'+'<br>'
                                to_hide = False
                                self.config_widget.children = self.configuration_software_tab().children
                                return
                else:
                    if (self.selected_slice_name.value != 'none'):
                        text="The selected slice has not been submitted. Please submit and configure your slice.<br>"
                        to_hide = True
                    else:
                        text = 'You have not selected any slice'
                        to_hide = True
                
                
        label = widgets.HTML(value=text)
        children = self.config_widget.children
        new_children = (children[0], label, children[2])
        self.config_widget.children = new_children
        if to_hide:
                self.config_widget.children[2].layout.visibility = 'hidden'
                self.config_widget.children[2].layout.display = 'none'
        else:
                self.config_widget.children[2].layout.visibility = 'visible'
                self.config_widget.children[2].layout.display = ''
        
        #print ('end update config wid:' + str(datetime.datetime.now()))  
        
    
    def update_my_notebook_widgets(self, change):
        """
        Updates the my notebooks dropdown widget

        """
        
        selected_value = change['new']
        children = self.run_notebooks_tab_widget.children
        my_nb_dir = self.path_structure['MyNotebooks']['MY_NOTEBOOKS_DIR']
        p_new = os.path.join(my_nb_dir, selected_value)
        btn = widgets.Button(description='Run Notebook')
        op = widgets.Output()
        t1 = 'open notebook using this link'
        if self.src:
            relative_path = self.get_relative_path_with_parent(p_new)
        else:
            relative_path = self.get_relative_path(p_new)
        with op:
            op.clear_output()
            display(Markdown(f"[{t1}]({relative_path})"))
        
        op1 = widgets.Output()
        btn.on_click(lambda b: self.run_notebook_using_btn_no_state(b, p_new, op1))
        
        new_child = widgets.VBox([children[1].children[0],children[1].children[1],widgets.HBox([op, btn]), op1, children[1].children[4]])
        new_children = (children[0], new_child, children[2], children[3])
        self.run_notebooks_tab_widget.children = new_children
        
        
        
        
    def update_output_notebook_widgets(self, change):
        """
        Updates the view ouput tab

        """
        selected_value = change['new']
        children = self.view_output_tab_widget.children
        my_nb_dir = self.path_structure['MyNotebooks']['MY_NOTEBOOKS_DIR']
        p_new = os.path.join(my_nb_dir, selected_value)
        btn = widgets.Button(description='Run Notebook')
        op = widgets.Output()
        t1 = 'click to modify your view output notebook'
        if self.src:
            relative_path = self.get_relative_path_with_parent(p_new)
        else:
            relative_path = self.get_relative_path(p_new)
        with op:
            op.clear_output()
            display(Markdown(f"[{t1}]({relative_path})"))
        
        op1 = widgets.Output()
        btn.on_click(lambda b: self.run_notebook_using_btn_no_state(b, p_new, op1))
        
        new_child = widgets.VBox([children[1].children[0],widgets.HBox([op, btn]), op1, children[1].children[3]])
        new_children = (children[0], new_child)
        self.view_output_tab_widget.children = new_children
        
    def refresh_my_notebooks(self, b, dropdown):
        """
        Refresh the dropdown values showing th list of files in the dir

        """
        my_nb_dir = self.path_structure['MyNotebooks']['MY_NOTEBOOKS_DIR']
        new_files = self.list_files(my_nb_dir)
        dropdown.options = new_files
        
    def refresh_slice_dirs(self, b, dropdown):
        """
        Refresh the dropdown values showing th list of saved slice dirs in slice_info

        """
        slice_info_dir = self.path_structure['Slice']['SLICE_INFO_DIR']
        saved_slice_dirs = self.list_slice_dirs(slice_info_dir)
        dropdown.options = saved_slice_dirs
        for widget in self.slice_info_tab_widget.children[1].children:
            widget.layout.visibility = 'visible'
            widget.layout.display = ''
        
        
    def get_state_from_fim(self, b, output):
        with output:
            output.clear_output()
            if self.selected_slice_name.value!='none':
                if self.slice_submitted.value is True:
                    n = self.selected_slice_name.value.replace("'", "").replace("\"", "")
                    if (n in self.fabric_slice_names):
                        self.logger.info(state.get_state_in_fim(n))
                else:
                    self.logger.info(state.read_state_from_local(self.selected_slice_name.value))
            else:
                self.logger.error('No slice selected.')
                
    
        
        
        
    
    # This function displays a tab that checks the prerequisite requirements to run experiments
    # 1. Displays a dropdown menu showing the list of "jupyter-examples" repos cloned in /home/fabric/work on JH
    # 2. Asks users to select from which jupyter examples repo they want to run configure.ipynb
    # 3. Display a button to run configure.ipynb automatically and a link to open the selected configure.ipynb 
    #    if users want to run the configure.ipynb themselves
    # 4. After users run configure.ipynb, the code checks the existence of files and installed libraries
    
    def prerequisite_tab(self):
        """
        Creates check prereqs widget

        :return: widget
        :rtype: widgets.VBox
        """
        
        # horizontal line separator
        separator = widgets.HTML("<hr style='height:2px;border-width:0;color:gray;background-color:gray;margin-top:5px;margin-bottom:10px;'/>")

        # Step 1: Configure Environment
        dropdown = widgets.Dropdown(
            options= ['none'] + self.get_existing_jupyter_examples_dirs(),
            description='jupyter-examples directories',
            style={'description_width': 'initial'},
            layout={'width': '400px'}
        )
        button1_step1 = widgets.Button(description="Select Directory")
        output1_step1 = widgets.Output()
        button1_step1.on_click(lambda b: self.prerequisite_step1_button1(b, output1_step1, dropdown))
        
        label_or = widgets.HTML('<div style="text-align: left; font-size: 16px; font-weight: bold; color: #000080;">OR</div>')
        textbox1_step1 = widgets.Text(
            placeholder='e.g, /home/fabric/work/folder/test.ipynb',
            description="Custom notebook path",
            style={'description_width': 'initial'},
            layout={'width': '500px'}
        )
        button2_step1 = widgets.Button(description="Select File")
        output2_step1 = widgets.Output()
        button2_step1.on_click(lambda b: self.prerequisite_step1_button2(b, output2_step1, textbox1_step1 ))
        
        button3_step1 = widgets.Button(description="Open Configure Notebook Link", layout={'width': '200px'})
        output3_step1 = widgets.Output()
        button3_step1.on_click(lambda b: self.prerequisite_step1_button3(b, output3_step1))
        button4_step1 = widgets.Button(description="Run Configure Notebook", layout={'width': '200px'})
        output4_step1 = widgets.Output()
        button4_step1.on_click(lambda b: self.prerequisite_step1_button4(b, output4_step1))

        box1_title = widgets.HTML("<h1 style='color: darkblue;'>Step 1: Configure the Environment</h1>")
        box1_des1 = widgets.HTML("<h2 style='color: darkblue;'>In this step, you will configure the environment by running the configure notebook. </h2>")
        box1_des2 = widgets.HTML("<h2 style='color: darkblue;'>Specify the location of configure notebook</h2>")
        box1_des3 = widgets.HTML("<h2 style='color: darkblue;'>Change values in configure notebook</h2>")
        box1_des4 = widgets.HTML("<h2 style='color: darkblue;'>Run configure notebook</h2>")
        box1 = widgets.VBox([box1_title,box1_des1, box1_des2, widgets.HBox([dropdown, button1_step1]), output1_step1, label_or, widgets.HBox([textbox1_step1, button2_step1]), output2_step1, box1_des3, button3_step1,output3_step1, box1_des4, button4_step1, output4_step1, separator])


        # Box 2: Check Existence of Files
        box2_title = widgets.HTML("<h1 style='color: darkgreen;'>Step 2: Check Existence of Files</h1>")
        box2_des1 = widgets.HTML("<h2 style='color: darkgreen;'>In this step, you can check whether files (as results of running configure.ipynb) exist . </h2>")
        button_check_files = widgets.Button(description="Check Existence")
        output_check_files = widgets.Output()
        button_check_files.on_click(lambda b: self.on_button_click_prerequisite_step2(b, output_check_files, self.JH_home_path))
        box2 = widgets.VBox([box2_title,box2_des1, widgets.HBox([button_check_files]), output_check_files])

        
        # Box3 Check Content of Files
        box3_title = widgets.HTML("<h1 style='color: mediumpurple;'>Step 3: Check Content of Files</h1>")
        button_check_files_content = widgets.Button(description="Check Content")
        output_check_files_content = widgets.Output()
        button_check_files_content.on_click(lambda b: self.on_button_click_prerequisite_step3(b, output_check_files_content, self.JH_home_path))
        #button_check_files.on_click(on_button_click_check_files)
        box3 = widgets.VBox([box3_title, widgets.HBox([button_check_files_content]), output_check_files_content])


        # Box 4: Check Libraries
        box4_title = widgets.HTML("<h1 style='color: darkred;'>Step 3: Check Libraries</h1>")
        button_check_libraries = widgets.Button(description="Check Libraries")
        output_check_libraries = widgets.Output()
        button_check_libraries.on_click(lambda b: self.on_button_click_prerequisite_step4(b, output_check_libraries))
        box4 = widgets.VBox([box4_title, widgets.HBox([button_check_libraries]), output_check_libraries])
        nextBtn = widgets.Button(description="Next")
        nextBtn.on_click(lambda b: self.next_tab(b))
        # Create a single tab with all the boxes and separators listed vertically
        tab1 = widgets.VBox([box1, box2, box3, box4, nextBtn])
        #check_prerequisite_tab.set_title(0, 'Check Prerequisite')
        return tab1
    
    
    
    def slice_info_tab(self):
        """
        Creates slice info widget

        :return: widget
        :rtype: widgets.VBox
        """
        # Add a horizontal line separator
        separator = widgets.HTML("<hr style='height:2px;border-width:0;color:gray;background-color:gray;margin-top:5px;margin-bottom:10px;'/>")
        # Step 1: Define slice
        paths_structure = self.path_structure
        box1_label = widgets.HTML("<h2 style='color: darkblue;'>Option1: Use Pre-Defined Topology</h2>")
        
        box1_label1 = widgets.Label(value="Specify Slice Name in load_variables.py")
        #box1_button1 = widgets.Button(description="Open Notebook Link")
        box1_output1= widgets.Output()
        p1 = paths_structure['Setup']['VARIABLES_FILE']
        #box1_button1.on_click(lambda b: self.slice_info_step1_btn1(b, box1_output1, p1))
        if self.src:
            relative_path = self.get_relative_path_with_parent(p1)
        else:
            relative_path = self.get_relative_path(p1)
        with box1_output1:
            box1_output1.clear_output()
            display(Markdown(f"[Open and modify slice name using this link]({relative_path})"))
        box1_part1 = widgets.VBox([box1_label, widgets.HBox([box1_label1, box1_output1])])
        
        box1_label2 = widgets.Label(value="Specify Topology Variables in topology_variables.ipynb")
        #box1_button2 = widgets.Button(description="Open Notebook Link")
        box1_output2= widgets.Output()
        p2= paths_structure['Slice']['SLICE_TOPOLOGY_VARIABLES']
        #box1_button2.on_click(lambda b: self.slice_info_step1_btn1(b, box1_output2, p2))
        if self.src:
            relative_path = self.get_relative_path_with_parent(p2)
        else:
            relative_path = self.get_relative_path(p2)
        #relative_path = self.get_relative_path(p2)
        with box1_output2:
            box1_output2.clear_output()
            display(Markdown(f"[Open and modify topology variables using this link]({relative_path})"))
        box1_part2 = widgets.VBox([widgets.HBox([box1_label2, box1_output2])])
        
        box1_label3 = widgets.Label(value="Define Your Slice Topology in define_slice.ipynb")
        #box1_button3 = widgets.Button(description="Open Notebook Link")
        box1_output3= widgets.Output()
        p3= paths_structure['Slice']['DEFINE_SLICE_NOTEBOOK']
        #box1_button3.on_click(lambda b: self.slice_info_step1_btn1(b, box1_output3, p3))
        if self.src:
            relative_path = self.get_relative_path_with_parent(p3)
        else:
            relative_path = self.get_relative_path(p3)
        #relative_path = self.get_relative_path(p3)
        with box1_output3:
            box1_output3.clear_output()
            display(Markdown(f"[Open and modify slice topology using this link]({relative_path})"))
        box1_part3 = widgets.VBox([widgets.HBox([box1_label3, box1_output3])])
        
        box1_button1 = widgets.Button(description='Confirm')
        box1_button1.style.button_color = 'green'
        b1_output1 = widgets.Output()
        box1_button1.on_click(lambda b, o=b1_output1: self.slice_by_modify_notebooks(b,o))
        
        box1_label4 = widgets.HTML("<h2 style='color: darkgray;'>Option2: Load Saved Topology</h2>")
        #box1_button4 = widgets.Button(description="Open Editor")
        box1_output4= widgets.Output()
        #box1_button4.on_click(lambda b: self.slice_info_step1_btn2(b, box1_output4,self.path_structure))
        #box1_button5 = widgets.Button(description="Close Editor")
        #box1_button5.on_click(lambda b: self.slice_info_step1_btn3(b, box1_output4))
        #open_close = widgets.HBox([box1_button4, box1_button5])
        box1_dropdown1 = widgets.Dropdown(
            options= self.list_slice_dirs(self.path_structure['Slice']['SLICE_INFO_DIR']),
            description='Saved Slices',
            style={'description_width': 'initial'},
            layout={'width': '400px'}
        )
        box1_refresh_btn = widgets.Button(description='Refresh')
        box1_refresh_btn.on_click(lambda b, d=box1_dropdown1: self.refresh_slice_dirs(b, d))
        box1_confirm_btn_2 = widgets.Button(description='Confirm')
        box1_confirm_btn_2.style.button_color = 'green'
        box1_confirm_btn_2.on_click(lambda b, o= box1_output4: self.load_saved_slice(b, o))     
        box1_part4 = widgets.VBox([box1_label4, widgets.HBox([box1_dropdown1,box1_refresh_btn]), box1_confirm_btn_2, box1_output4])
        box1_title = widgets.HTML("<h1 style='color: darkblue;'>Step 1: Define Your Slice</h1>")
        
        box1 = widgets.VBox([box1_title, box1_part1, box1_part2, box1_part3, box1_button1, b1_output1,box1_part4, separator])
        
        # Box 2: Add features before submit
        box2_title = widgets.HTML("<h1 style='color: darkgreen;'>Step 2(Optional): Options Before Submitting Slice </h1>")
        # Create checkboxes
        box2_checkbox1 = widgets.Checkbox(description="random sites")
        #box2_button1= widgets.Button(description="Open Notebook")
        box2_output1 = widgets.Output()
        p21 = paths_structure['Slice']['RANDOM_SITES_NOTEBOOK']
        t1 = 'click to check random_sites notebook. No need to modify'
        if self.src:
            relative_path = self.get_relative_path_with_parent(p21)
        else:
            relative_path = self.get_relative_path(p21)
        #relative_path = self.get_relative_path(p21)
        with box2_output1:
            box2_output1.clear_output()
            display(Markdown(f"[{t1}]({relative_path})"))
        #box2_button1.on_click(lambda b: self.slice_info_step1_btn5(b, box2_output1, p21, t1))
        
        box2_checkbox2 = widgets.Checkbox(description="random ptp sites")
        #box2_button2= widgets.Button(description="Open Notebook")
        box2_output2 = widgets.Output()
        p22 = paths_structure['Slice']['RANDOM_PTP_SITES_NOTEBOOK']
        t2 = 'click to view random_ptp_sites notebook. No need to modify'
        #box2_button2.on_click(lambda b: self.slice_info_step1_btn5(b, box2_output2, p22, t2))
        if self.src:
            relative_path = self.get_relative_path_with_parent(p22)
        else:
            relative_path = self.get_relative_path(p22)
        #relative_path = self.get_relative_path(p22)
        with box2_output2:
            box2_output2.clear_output()
            display(Markdown(f"[{t2}]({relative_path})"))
        
        box2_checkbox3 = widgets.Checkbox(description="generate graphml")
        #box2_button3= widgets.Button(description="Open Notebook")
        box2_output3 = widgets.Output()
        p23 = paths_structure['Slice']['GENERATE_GRAPHML_NOTEBOOK']
        t3 = 'click to view graphml notebook. No need to modify'
        #box2_button3.on_click(lambda b: self.slice_info_step1_btn5(b, box2_output3, p23, t3))
        if self.src:
            relative_path = self.get_relative_path_with_parent(p23)
        else:
            relative_path = self.get_relative_path(p23)
        #relative_path = self.get_relative_path(p23)
        with box2_output3:
            box2_output3.clear_output()
            display(Markdown(f"[{t3}]({relative_path})"))
        
        box2_checkbox4 = widgets.Checkbox(description="post boot script")
        #box2_button4= widgets.Button(description="Open Notebook")
        box2_output4 = widgets.Output()
        p24 = [paths_structure['Slice']['POST_BOOT_SCRIPT']]+[paths_structure['Slice']['POST_BOOT_NOTEBOOK']]
        t4 = ['click to modify the post boot script', 'click to modify the post boot notebook']
        #box2_button4.on_click(lambda b: self.slice_info_step1_btn4(b, box2_output4, p24, t4))
        with box2_output4:
            box2_output4.clear_output()
            if (isinstance(p24, type(t4)) and isinstance(t4, list)):
                markdown_text = ''
                if self.src:
                    for i in range(len(t4)):
                        markdown_text += f"[{t4[i]}]({self.get_relative_path_with_parent(p24[i])})" + ' '
                else:
                    for i in range(len(t4)):
                        markdown_text += f"[{t4[i]}]({self.get_relative_path(p24[i])})" + ' '
                display(Markdown(markdown_text))
        
        for i, checkbox in enumerate([box2_checkbox1, box2_checkbox2, box2_checkbox3, box2_checkbox4]):
            checkbox.observe(lambda change: self.update_slice_info_checkbox(change), names='value')
        
        checkbox_box = widgets.VBox([widgets.HBox([box2_checkbox1, box2_output1]), widgets.HBox([box2_checkbox2, box2_output2]), widgets.HBox([box2_checkbox3, box2_output3]), widgets.HBox([box2_checkbox4, box2_output4])]) 
        box2_output= widgets.Output()
        box2_button = widgets.Button(description="Add Options", layout=widgets.Layout(width='200px'))
        box2 = widgets.VBox([box2_title, checkbox_box, box2_button, box2_output, separator])
        box2_button.on_click(lambda b: self.add_slice_options(b, box2_output))
        
        # Box 3: Submit Your Slice
        box3_title = widgets.HTML("<h1 style='color: mediumpurple;'>Step 2: Submit Your Slice</h1>")
        
        box3_output= widgets.Output()
        box3_button = widgets.Button(description="Submit slice")
        
        showState = widgets.Button(description="State")
        op = widgets.Output()
        showState.on_click(lambda b: self.get_state_from_fim(b, op))
        
        op1 = widgets.Output()
        box3 = widgets.VBox([box3_title, box3_button, box3_output, showState, op, separator])
        box3_button.on_click(lambda b: self.submit_slice_using_btn(b,box3_output))
        
        
        # Box4: Configure Your Slice
        box4_title = widgets.HTML("<h1 style='color: darkred;'>Step 4: Install Software and Configuration</h1>")
        box4_output= widgets.Output()
        #box4_button1 = widgets.Button(description="Open Configure Notebook", layout=widgets.Layout(width='200px'))
        box4_link_op = widgets.Output()
        p41 = paths_structure['Config']['CONFIG_SLICE_NOTEBOOK']
        if self.src:
            relative_path = self.get_relative_path_with_parent(p41)
        else:
            relative_path = self.get_relative_path(p41)
        t5 = 'click to modify configure slice notebook.'
        #box4_button1.on_click(lambda b: self.slice_info_step1_btn5(b, box4_output, p41, t5))
        with box4_link_op:
            box4_link_op.clear_output()
            display(Markdown(f"[{t5}]({relative_path})"))
        box4_button2 = widgets.Button(description="Run Configure Notebook", layout=widgets.Layout(width='200px'))
        config_slice_nb_path = paths_structure['Config']['CONFIG_SLICE_NOTEBOOK']
        box4_button2.on_click(lambda b: self.run_notebook_using_btn(b, config_slice_nb_path, box4_output))
        
        
        showState1 = widgets.Button(description="State")
        op1 = widgets.Output()
        showState1.on_click(lambda b: self.get_state_from_fim(b, op1))
        
        box4 = widgets.VBox([box4_title, widgets.HBox([box4_link_op,box4_button2]), box4_output, showState1, op1, separator])
        nextBtn = widgets.Button(description="Next")
        nextBtn.on_click(lambda b: self.next_tab(b))
        # Remove box2 options and box4
        tab2= widgets.VBox([box1, box3, nextBtn])
        return tab2
    
    
    
    def configuration_software_tab_original(self):
        """
        Creates config tab

        :return: widget
        :rtype: widgets.VBox
        """
        separator = widgets.HTML("<hr style='height:2px;border-width:0;color:gray;background-color:gray;margin-top:5px;margin-bottom:10px;'/>")
        box_title = widgets.HTML("<h1 style='color: darkblue;'>Install Software and Configuration</h1>")
        box_info = widgets.VBox([widgets.Label(value="You have not selected any slice")])
        box = widgets.VBox([box_title, box_info, separator])
        return box
    
    
    
    def configuration_software_tab(self):
        """
        Creates a tab that deals with configuration and software installation
        
        :return: widget
        :rtype: widgets.Vbox
        """
        separator = widgets.HTML("<hr style='height:2px;border-width:0;color:gray;background-color:gray;margin-top:5px;margin-bottom:10px;'/>")
        paths_structure = self.path_structure
        # Box4: Configure Your Slice
        box4_title = widgets.HTML("<h1 style='color: darkrblue;'>Install Software and Configuration</h1>")
        l = widgets.HTML(value='')
        box4_output= widgets.Output()
        box4_link_op0 = widgets.Output()
        box4_link_op = widgets.Output()
        p40 = paths_structure['Slice']['SLICE_INFO_DIR']
        final_topo_var_path = os.path.join(p40, self.selected_slice_name.value.replace("'", "").replace("\"", ""), 'topology_variables.ipynb')
        if self.src:
            r_path = self.get_relative_path_with_parent(final_topo_var_path)
        else:
            r_path = self.get_relative_path(final_topo_var_path)
        t4 = 'click to modify topology variables.'
        with box4_link_op0:
            box4_link_op0.clear_output()
            display(Markdown(f"[{t4}]({r_path})"))
            
        p41 = paths_structure['Config']['CONFIG_SLICE_NOTEBOOK']
        if self.src:
            relative_path = self.get_relative_path_with_parent(p41)
        else:
            relative_path = self.get_relative_path(p41)
        t5 = 'click to modify configure slice notebook.'
        #box4_button1.on_click(lambda b: self.slice_info_step1_btn5(b, box4_output, p41, t5))
        with box4_link_op:
            box4_link_op.clear_output()
            display(Markdown(f"[{t5}]({relative_path})"))
        box4_button2 = widgets.Button(description="Run Configure Notebook", layout=widgets.Layout(width='200px'))
        config_slice_nb_path = paths_structure['Config']['CONFIG_SLICE_NOTEBOOK']
        box4_button2.on_click(lambda b: self.run_config_notebook_with_arg(b, config_slice_nb_path, box4_output, self.selected_slice_name.value.replace("'", "").replace("\"", "")))
        
        showState1 = widgets.Button(description="State")
        op1 = widgets.Output()
        showState1.on_click(lambda b: self.get_state_from_fim(b, op1))
        part  = widgets.VBox([box4_link_op0, widgets.HBox([box4_link_op,box4_button2]), box4_output, showState1, op1, separator])
        
        box4 = widgets.VBox([box4_title, l, part])
        
        return box4
    
    
    def mflib_service_tab(self):
        """
        Creates mflib services widget

        :return: widget
        :rtype: widgets.VBox
        """
        elk_checkbox = widgets.Checkbox(value=False, description="ELK Stack")
        elk_checkbox_tooltip = "Instrumentize the ELK Stack and view Elasticsearch Data in Kibana dashboards"
        elk_icon = self.create_info_icon(elk_checkbox_tooltip)

        prometheus_checkbox = widgets.Checkbox(value=False, description="Prometheus")
        prometheus_checkbox_tooltip = "Instrumentize Promethus and view Prometheus metrics in Grafana dashboards"
        prometheus_icon = self.create_info_icon(prometheus_checkbox_tooltip)

        #precision_timing_checkbox = widgets.Checkbox(value=False, description="Precision Timing")
        #precision_timing_checkbox_tooltip = "Demo the usage of precision timing"
        #precision_timing_icon = self.create_info_icon(precision_timing_checkbox_tooltip)

        timestamp_checkbox = widgets.Checkbox(value=False, description="Precision Timing")
        timestamp_checkbox_tooltip = "Demo the usage of PTP timestamp. Record precision timestamp of packets and user-defined events and view it in InfluxDB. To run this experiment, the topology is expected to have more than two nodes, each located on a PTP-capable site. Nodes should be reachable to each other (layer 3 e.g, fabnet ipv4)"
        timestamp_icon = self.create_info_icon(timestamp_checkbox_tooltip)

        data_export_import_checkbox = widgets.Checkbox(value=False, description = "Data Transfer service")
        data_export_import_checkbox_tooltip="Export ELK/Prometheus data via snapshots and import the data in another Fabric slice. Transfer ELK data to Google Bigquery"
        data_export_import_icon = self.create_info_icon(data_export_import_checkbox_tooltip)

        owl_checkbox = widgets.Checkbox(value=False, description="One-Way-Latency (OWL)")
        owl_checkbox_tooltip = "Measure one way latency among Fabric sites. To run OWL, the topology is expected to have more than two nodes, each located on a PTP-capable site. Nodes should be reachable to each other (layer 3 e.g, fabnet v4)"
        owl_icon = self.create_info_icon(owl_checkbox_tooltip)
        
        for i, checkbox in enumerate([elk_checkbox, prometheus_checkbox, timestamp_checkbox, data_export_import_checkbox, owl_checkbox]):
            checkbox.observe(lambda change: self.update_mflib_notebooks_widget(change), names='value')
            checkbox.observe(lambda change: self.update_mflib_service_widget(change), names='value')
            checkbox.observe(lambda change: self.update_view_measurements_tab_widget(change), names='value')
            
        checkbox_box = widgets.VBox([widgets.HBox([elk_checkbox, elk_icon]), widgets.HBox([prometheus_checkbox, prometheus_icon]), widgets.HBox([timestamp_checkbox, timestamp_icon]), widgets.HBox([data_export_import_checkbox, data_export_import_icon]), widgets.HBox([owl_checkbox, owl_icon])])   
        box_title = widgets.HTML("<h1 style='color: darkblue;'>Optionally Select the MFLib Services</h1>")
        nextBtn = widgets.Button(description="Next")
        nextBtn.on_click(lambda b: self.next_tab(b))
        acc = widgets.Accordion()
        tab3 = widgets.VBox([box_title, checkbox_box, acc, nextBtn])
        
        return tab3
    
    
    def run_notebooks_tab(self):
        """
        Creates run notebooks widget

        :return: widget
        :rtype: widgets.VBox
        """
        separator = widgets.HTML("<hr style='height:2px;border-width:0;color:gray;background-color:gray;margin-top:5px;margin-bottom:10px;'/>")
        box_title = widgets.HTML("<h1 style='color: darkblue;'>Run Experiments</h1>")
        box1_title = widgets.HTML("<h2 style='color: darkred;'>My Notebooks</h2>")
        box1_info = widgets.VBox()
        my_nb_dir = self.path_structure['MyNotebooks']['MY_NOTEBOOKS_DIR']
        files = self.list_files(my_nb_dir)
        box1_dropdown = widgets.Dropdown(
            options= files,
            description='my notebooks',
            style={'description_width': 'initial'},
            layout={'width': '300px'}
        )
        refresh_btn = widgets.Button(description = 'Refresh')
        refresh_btn.on_click(lambda b, d=box1_dropdown: self.refresh_my_notebooks(b, d))
        p = os.path.join(my_nb_dir, box1_dropdown.value)
        btn = widgets.Button(description='Run Notebook')
        op = widgets.Output()
        t1 = 'open notebook using this link'
        if self.src:
            relative_path = self.get_relative_path_with_parent(p)
        else:
            relative_path = self.get_relative_path(p)
        with op:
            op.clear_output()
            display(Markdown(f"[{t1}]({relative_path})"))
        
        op1 = widgets.Output()
        btn.on_click(lambda b: self.run_notebook_using_btn_no_state(b, p, op1))
        box1_dropdown.observe(self.update_my_notebook_widgets, names='value')

        #interactive_widget = widgets.interactive(self.update_my_notebook_widgets, dropdown_widget=box1_dropdown)
        box1 = widgets.VBox([box1_title,widgets.HBox([box1_dropdown, refresh_btn]),widgets.HBox([op, btn]), op1, separator])
        box2_title = widgets.HTML("<h2 style='color: mediumpurple;'>MFLib Notebooks</h2>")
        box2_info = widgets.VBox([widgets.Label(value = 'You have not selected any MFLib services')])
        box2 = widgets.VBox([box2_title, box2_info, separator])
        nextBtn = widgets.Button(description="Next")
        nextBtn.on_click(lambda b: self.next_tab(b))
        tab4 = widgets.VBox([box_title, box1, box2, nextBtn])
        return tab4
    
    def view_output_tab(self):
        """
        Creates view output widget

        :return: widget
        :rtype: widgets.VBox
        """
        separator = widgets.HTML("<hr style='height:2px;border-width:0;color:gray;background-color:gray;margin-top:5px;margin-bottom:10px;'/>")
        box_title = widgets.HTML("<h1 style='color: darkblue;'>View Output</h1>")
        box_info = widgets.VBox([widgets.Label(value="Select the notebook to run")])
        my_nb_dir = self.path_structure['MyNotebooks']['MY_NOTEBOOKS_DIR']
        files = self.list_files(my_nb_dir)
        box1_dropdown = widgets.Dropdown(
            options= files,
            description='view output notebooks',
            style={'description_width': 'initial'},
            layout={'width': '300px'}
        )
        refresh_btn = widgets.Button(description='Refresh')
        refresh_btn.on_click(lambda b, d=box1_dropdown: self.refresh_my_notebooks(b, d))
        p = os.path.join(my_nb_dir, box1_dropdown.value)
        btn = widgets.Button(description='Run Notebook')
        op = widgets.Output()
        t1 = 'open notebook using this link'
        if self.src:
            relative_path = self.get_relative_path_with_parent(p)
        else:
            relative_path = self.get_relative_path(p)
        with op:
            op.clear_output()
            display(Markdown(f"[{t1}]({relative_path})"))
        
        op1 = widgets.Output()
        btn.on_click(lambda b: self.run_notebook_using_btn_no_state(b, p, op1))
        box1_dropdown.observe(self.update_output_notebook_widgets, names='value')
        box1 = widgets.VBox([widgets.HBox([box1_dropdown, refresh_btn]),widgets.HBox([op, btn]), op1, separator])
        box = widgets.VBox([box_title, box1])
        return box
        
    def view_measurements_tab(self):
        """
        Creates view measurements widget

        :return: widget
        :rtype: widgets.VBox
        """
        separator = widgets.HTML("<hr style='height:2px;border-width:0;color:gray;background-color:gray;margin-top:5px;margin-bottom:10px;'/>")
        box_title = widgets.HTML("<h1 style='color: darkblue;'>View Measurements</h1>")
        box_info = widgets.VBox([widgets.Label(value="Please instrumentize ELK and Prometheus")])
        box = widgets.VBox([box_title, box_info, separator])
        return box
        
    
    def slice_state_tab(self):
        """
        Creates slice state widget

        :return: widget
        :rtype: widgets.VBox
        """
        separator = widgets.HTML("<hr style='height:2px;border-width:0;color:gray;background-color:gray;margin-top:5px;margin-bottom:10px;'/>")
        box_title = widgets.HTML("<h1 style='color: darkblue;'>Slice State</h1>")
        box_info = widgets.VBox([widgets.Label(value="You have not selected any slice")])
        box = widgets.VBox([box_title, box_info, separator])
        return box
        
   
    def display_gui(self):
        display(self.main_tab)
        
    
if __name__ == "__main__":
    EF=ExperimentFramework()
    