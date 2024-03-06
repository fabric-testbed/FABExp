# Fabric Experiment Framework

## Description

The FABRIC Experiment Framework is a user-friendly framework built on top of ipywidgets, designed to enhance users' experience running their experiments(in Jupyter Notebooks) within the FABRIC testbed.  By leveraging these interactive widgets, the framework provides users with an intuitive Graphical User Interface (GUI) for efficiently checking the prerequisites(JupyterHub Environment settings for FABRIC experiments), smoothly running their experiments and easily tracking experiment states.

## Key Features

1. **Interactive Widgets:** Leverage ipywidgets to seamlessly integrate buttons, dropdowns, accordions and other interactive elements into Jupyter notebooks. 

2. **Experiment State Management:** Easily monitor the state of expriments. Users can seamlessly resume their work from where they left off, ensuring a smooth and continuous workflow.

## Structure
```md
ExperimentFramework/
├── README.md
├── welcome.ipynb
├── FABExp.py
├── template
│   ├── Start_Here.ipynb
│   ├── paths.cfg
│   ├── run_experiment
│   │   ├── install
│   │   │   ├── install_docker.ipynb
│   │   │   └── install_ptp.ipynb
│   │   ├── mflib_experiments
│   │   │   ├── data_transfer_via_snapshot
│   │   │   │   ├── create_single_node_backup.ipynb
│   │   │   │   ├── elk_export.ipynb
│   │   │   │   ├── elk_import.ipynb
│   │   │   │   ├── prometheus_export.ipynb
│   │   │   │   ├── prometheus_import.ipynb
│   │   │   │   └── snapshots
│   │   │   │       └── snapshot_test.tar
│   │   │   ├── export_elk_data_to_bigquery
│   │   │   │   ├── elk_bq_query_data.ipynb
│   │   │   │   ├── elk_bq_setup.ipynb
│   │   │   │   ├── elk_bq_upload_data.ipynb
│   │   │   │   └── google_service_account_key
│   │   │   │       └── key.json
│   │   ├── instrumentize
│   │   │   │   ├── dashboard_examples
│   │   │   │   │   ├── grafana
│   │   │   │   │   │   ├── node_exporter_full.json
│   │   │   │   │   │   └── up.json
│   │   │   │   │   └── kibana
│   │   │   │   │       ├── FABRICDashboardSample.ndjson
│   │   │   │   │       └── FABRICDashboards.ndjson
│   │   │   │   ├── mflib_add_meas_node_after_submit.ipynb
│   │   │   │   ├── mflib_elk_kibana.ipynb
│   │   │   │   ├── mflib_init.ipynb
│   │   │   │   ├── mflib_instrumentize_elk.ipynb
│   │   │   │   ├── mflib_instrumentize_promtheus.ipynb
│   │   │   │   └── mflib_prometheus_grafana.ipynb
│   │   │   ├── one_way_latency
│   │   │   │   ├── owl_demo1.ipynb
│   │   │   │   ├── owl_demo2.ipynb
│   │   │   └── precision_timing
│   │   │       ├── dashboard_examples
│   │   │       │   └── influxdb
│   │   │       │       ├── influxdb_timestamp(paste on UI).json
│   │   │       │       └── influxdb_timestamp_dashboard.yml
│   │   │       ├── demo_precision_timing.ipynb
│   │   │       ├── record_precision_timestamp.ipynb
│   │   │       ├── tools
│   │   │       │   ├── start_dump.sh
│   │   │       │   └── stop_dump.sh
│   │   │       └── visualize_precision_timestamp.ipynb
│   │   └── my_experiments
│   │       ├── main.ipynb
│   │       ├── notebook1.ipynb
│   │       └── notebook2.ipynb
│   ├── config_and_install_sw
│   │   ├── config_slice.ipynb
│   ├── runtime_info
│   │   ├── cur_state_info
│   │   │   └── state.json
│   │   └── logs
│   │       └── log.log
│   ├── setup
│   │   ├── config
│   │   │   ├── dependencies.json
│   │   │   └── load_variables.py
│   │   ├── include
│   │   │   └── include_libraries.py
│   │   └── install
│   │       └── install_libraries.ipynb
│   ├── slice_info
│   │   ├── write_value.py
│   │   ├── define_slice.ipynb
│   │   ├── submit_slice.ipynb
│   │   └── topology_variables.ipynb
│   └── std_notebook_lib
│       ├── exp_framework_lib
│       │   ├── ExperimentFramework.py
│       │   └── state.py
│       └── mflib
│           └── mflib-data-files
│               └── __init__.py
```

**README.md**: This file.

**welcome.ipynb**: a notebook with a wrapper GUI that starts the Experiment framework.

**/template/**: the folder where all the experiment notebooks and code locate. The **/template/** folder will be copied to the new directory when users create new expriment directories and the working directory changes to the newly created dir when users click the 'Go to Experiment' button.  

## Installation

Currently available via zip package. Will be available on github where users can run 'git clone' to download it. 


## Usage

Users can go to **welcome.ipynb** to start.

**welcome.ipynb:** Run the cell to start the GUI. Users can create/delete experiment directories using the buttons. Use the dropdown menu to select the experiment and click the 'Go to Experiment' button, it will run **start_here.ipynb** inside the selected directory to pop up new GUI.

### Tabs
#### **1.check prereqs:** 

Starting from jupyter-examples rel 1.6.1, configure_and_validate.ipynb is available to users to validate their Fabric settings in JH. It is a preferred way to check the envirnment settings. The old configure.ipynb is still left there for backward compatibility. Users can run either notebook to set up their environment.

1. Users can select the jupyter examples directory using the dropdown menu or manually input the directory name using the textbox to specify which *configure.ipynb* or *configure_and_validate.ipynb*(available after jupyter-examples 1.6.1) they want to run. By default, if both of the two files are available in the directory the user selects, the code prioritize *configure_and_validate.ipynb* since the notebook checks the JH settings and auto generate config for users if something is not correctly set. 

2. After the path of *configure.ipynb* or *configure_and_validate.ipynb* is specified, users can open the notebook to input values such as FABRIC_PROJECT_ID (and other values if they use *configure.ipynb*). Once finished, the 'Run Configure Notebook' button can be used to run the selected configure notebook, which uses nbconvert(for configure.ipynb) or ipython run magic(for configure_and_validate) to run the entire notebook and display the output.

3. The **'Check Existence'** button checks whether the files exist by inspecting the content of *configure.ipynb*. It reads *configure.ipynb* and finds the paths of files(defined by EXPORT) and then checks whether the files exist based on the given paths **Note: The SSH tunnel zip file is not checked at this moment. This part of the GUI will be hidden if user selects configure_and_validate.ipynb**.

4. The **'Check Content'** button checks whether the content in the FABRIC_RC, FABRIC_SSH_CONFIG file matches what the users specify in *configure.ipynb*. Besides this, it also validates the fields such as FABRIC_PROJECT_ID, SSH keys by calling the FABRIC CORE API. **Note: FABRIC_BASHION_USERNAME is not validated at this moment by the code. Users can run configure_and_validate.ipynb to validate it. This part of the GUI will be hidden if user selects configure_and_validate.ipynb**.

5. The **'Check Libraries'** button checks whether the library versions match or not. Library versions are specified in requirements.txt(assumed to be in the same dir as configure.ipynb) and running 'pip list' returns the library versions actually installed. The difference is returned as the result.**Note: This part of the GUI will be hidden if user selects configure_and_validate.ipynb**

**The check in 3,4,5 will pass if users do run configure.ipynb. They need to rerun configure.ipynb if there is failure in 3,4,5**


#### **2.slice_info:** 
Users have two options to define their slice:

1. Option 1: The first three files are the ones users need to modify to set up their slices(slice_name, topology_variables and define_slice). **Click the 'Confirm' button when you finish modifying these files.** If there is no conflict of the slice names, a new folder named after the slice name will be created which stores the define_slice.ipynb and topology_variables.ipynb for that slice.

2. Option 2: Load a saved topology. Users can always come back and find the info of slice they created within the selected experment. They can use this option to load the topology of a slice (either submitted or not submitted and continue)

3. If users create new slices, they need to **'Submit Slice'**. If users load a slice that has been submitted, the GUI will display info on what to do next. Clicking the buttons will run the corresponding jupyter notebooks with the run_line_magic command and the output will be the same as what you see when you 'run all cell' in a notebook.

4. After running the notebooks, a unique **state** will be recorded both locally and to the FABRIC Fim model. For example, clicking the **'Submit Slice'** button will run the 'submit_slice' notebook and 'SLICE_SUBMITTED' will be appended to the state if there is no exception runing the notebook. 

#### **3.MFLib Services**

The Measurement Framework Library provides various services to help users monitor and manage the data inside their experiments. Users can use the checkboxes to select the services they want to add. The corresponding accordion(showing which notebooks users need to run to satisfy the prerequisite of the selected experiment) will pop up if any box is checked.

1. **ELK Stack/Prometheus**: **ELK Stack** consists of Elasticsearch, Logstash and Kibana. By instrumentizing ELK, the Elasticsearch database will run on the measurement node and collect data from the expeeriment nodes using Beats(Filebeat, Packetbeat, metricbeat). The data can be visualized in Kibana using the dashboards. **Prometheus** collects metrics from the experiment nodes using different exporters and the data can be visualized in Grafana.

2. **Precision Timing** In this set of expriments, users can explore the difference between using Precision Time Protocol(PTP) and using regular Network Time Protocol(NTP). Users can record the precision timestamps of both the packets and user-defined events and visualize the timestamp data in InfluxDB.

3. **Data Transfer service** Once users instrumentize ELK or Prometheus, they may want to backup their data. In this set of expriments, users can explore how to save the data of ELK and Prometheus as **snapshots** and export the data to either another FABRIC slice or local machine for the backup. They can also restore and view thee data using th snapshot files. If users want to backup the data in cloud, examples of exporting ELK data to Google Bigquery are also available.

4. **One-Way-latency(owl)** Program for measuring one-way latency between nodes in FABRIC testbed. Though it is written specifically for FABRIC Testbed, it should work in a general setting with minimal edits, if at all. As outlined below, it can be used either within the Measurement Framework environment or as a stand-alone application possibly running inside a Docker contaier. Under all circumstances, the sender and receiver nodes must have PTP (Precision time Protocol) service running. Users can start the owl service and view the collected latency data.

**By checking the checkboxes under this tab, users will see dynamic accordion widgets in the current tab(3.MFLib Services) and in the next tab(4.Run Experiments) what they need to do to start the expriments, and the experiment notebooks**


#### **4.Run Notebooks**

By default, *main.ipynb* is the experiment notebook we rewrite for the selected experiment package. Users can copy their experiment code to the notebooks in my notebooks(They can also create new notbooks and refresh the gui). For example, in a FABExp package that creates a l3 fabnet IPv4 network, we may just provide the simple ping test in main (as a mock-up expriment). Users can do whatever they want, e.g, iperf tests and etc. If users select the MFLib services in the previous tab, they can also run the MFLib experiments following instructions in the GUI. Users can also ssh to the nodes using the open terminal button.


#### **5.View Output**

Similar to **4.Run Notebooks**, users can copy their code to the notebook and run it if they have a notebook to view the experiment output.

#### **See Measurements**
If users select ELK/Prometheus in **3.MFLib services**, and finish instrumentizing ELK/promtheus, they can run the resulting notebooks to set up ssh tunnels to view the data in Kibana/Grafana.

#### **Slice State**
Users can alway switch to this tab to view the state of the selected slice. The widget is dynamic. When there is an update on the state, the tab will be updated automatically. At this moment, the Experiment Framework tracks the following states:

* "SLICE_DEFINED"
* "SLICE_SUBMITTED"
* "SLICE_CONFIGURED"
* "MEAS_NODE_ADDED"
* "MFLIB_INITIATED"
* "ELK_INSTRUMENTIZED"
* "PROMETHEUS_INSTRUMENTIZED"
* "PTP_INSTALLED"
* "DOCKER_INSTALLED"

Users can add custom state for their own experiments following the style of notebooks.











