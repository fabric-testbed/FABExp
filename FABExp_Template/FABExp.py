import ipywidgets as widgets
from IPython.core.getipython import get_ipython
from IPython.display import display, HTML, Javascript
import os
import shutil

if 'original_dir' not in globals():
    # Save the current working directory
    original_dir = os.getcwd()
os.environ['external'] = 'False'

# function to create a new experiment directory by copying the template dir
def create_new_exp(btn, text_box, dropdown, output):
    #print (os.getcwd())
    os.chdir(original_dir)
    new_dir_name = text_box.value.strip()
    with output:
        output.clear_output()
        if new_dir_name:
            source_dir = 'template'
            new_dir_path = os.path.join(os.getcwd(), new_dir_name)

            try:
                shutil.copytree(source_dir, new_dir_path)
                update_dropdown(dropdown)
                print(f"New experiment directory '{new_dir_name}' created successfully.")
            except FileExistsError:
                print(f"Error: Directory '{new_dir_name}' already exists.")
        else:
            print("Error: Please enter a valid directory name.")

# Function to run a notebook given the path           
def run_notebook(notebook_path):
    # Get the directory of the notebook
    notebook_dir = os.path.dirname(notebook_path)

    # change working dir
    print ('Changing working dir to:')
    get_ipython().run_line_magic('cd', notebook_dir)
    print (f'Running {notebook_path}')
    print ('')
    
    # execute the notebook
    get_ipython().run_line_magic('run', notebook_path)
            
# Function to run the 'start_here.ipynb' in the selected dir
def go_to_exp(btn, dropdown, output):
    os.environ['external'] = 'True'
    with output:
        output.clear_output()
        selected_dir = dropdown.value
        if selected_dir:
            os.chdir(original_dir)
            abs_path = os.path.abspath(selected_dir)
            nb_path = os.path.join(abs_path, 'Start_Here.ipynb')
            if (os.path.exists(nb_path)):
                run_notebook(nb_path)
            else:
                print (f'Start_Here.ipynb not found in {abs_path}')
                
        else:
            print("Error: Please select a directory.")

# Function to delete the selected experimnt            
def delete_exp(b, dropdown, output):
    with output:
        output.clear_output()
        selected_dir = dropdown.value
        if selected_dir:
            os.chdir(original_dir)
            abs_path = os.path.abspath(selected_dir) 
        confirm_output = widgets.Output()
        yes_button = widgets.Button(description="Yes")
        no_button = widgets.Button(description="No")
        confirm_widget = widgets.VBox([widgets.Label("Are you sure you want to delete the experiment?"), widgets.HBox([yes_button, no_button])])
        yes_button.on_click(lambda b: on_yes_click(output, confirm_widget,dropdown, abs_path))
        no_button.on_click(lambda b: on_no_click(output, confirm_widget))
        display(confirm_widget)

# remove the dir when yes is clicked            
def on_yes_click(out, confirm_widget,dropdown, abs_path):
    with out:
        out.clear_output(wait=True)
        try:
            shutil.rmtree(abs_path)
            print(f"Experiment '{abs_path}' has been deleted.")
            update_dropdown(dropdown)
        except FileNotFoundError:
            print(f"Experiment '{abs_path}' not found.")
        except OSError as e:
            print(f"Error: {e}")
        confirm_widget.close()

# Close the widget when no is clicked        
def on_no_click(out, confirm_widget):
    with out:
        out.clear_output(wait=True)
        confirm_widget.close()

# Function to update the dropdown with current directories
def update_dropdown(dropdown):
    os.chdir(original_dir)
    current_dirs = [d for d in os.listdir() if os.path.isdir(d) and not d.startswith('.') and d != 'template' and d!= '__pycache__']
    dropdown.options = current_dirs

# Create widgets
def create_wid():
    title = widgets.HTML("<h1 style='color: darkblue;'>Experiment Framework</h1>")
    text_box = widgets.Text(placeholder='Enter new experiment directory name')
    create_exp_button = widgets.Button(description='Create New Experiment', layout={'width': '200px'})
    output1 = widgets.Output()
    #create_exp_button.on_click(lambda b: create_new_exp(b, output1))

    dropdown = widgets.Dropdown(options=[], description='Select Existing Experiment', style={'description_width': 'initial'}, layout={'width': '300px'})
    go_to_exp_button = widgets.Button(description='Go to Experiment', layout={'width': '200px'})
    delete_exp_button = widgets.Button(description='Delete Experiment', layout={'width': '200px'})
    delete_exp_button.style.button_color = 'red'
    output2 = widgets.Output()
    gui = widgets.VBox([title, widgets.HBox([text_box,create_exp_button]),output1, widgets.HBox([dropdown, go_to_exp_button, delete_exp_button]), output2 ])
    return gui

def display_gui():
    gui = create_wid()
    display(gui)
    gui.children[1].children[1].on_click(lambda b: create_new_exp(b, gui.children[1].children[0],gui.children[3].children[0], gui.children[2]))
    gui.children[3].children[2].on_click(lambda b: delete_exp(b,gui.children[3].children[0], gui.children[4]))
    gui.children[3].children[1].on_click(lambda b: go_to_exp(b,gui.children[3].children[0],gui.children[4]))
    update_dropdown(gui.children[3].children[0])
    os.chdir(original_dir)
    
    

