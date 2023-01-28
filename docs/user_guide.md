# User guide

For the following sections it's assumed you already followed the instructions in the [installation guide](installation.md), and have a reptilearn directory with the same structure as this repository.

## Initial configuration

The main config file of the system can be found at [`system/config/config.py`](../system/config/config.py). You can either make changes to this file or make a copy inside the `system/config` directory (e.g. `system/config/my_config.py`), and tell the system to use that config file instead (see below how to do that). 

In any case, some attributes you may want to change at this point are:

- __api_port__: This is the port of the HTTP API that is used to control the system. You may want to change this value to prevent collisions with other software. It is used by the web UI, so any change requires also changing the value of the variable `api_url` in [`ui/src/config.js`](../ui/src/config.js).
- __state_store_address__: Another server running in the background is the state store server (see below for more information). This attribute should be a tuple (host, port). The port can be changed to any available port number. In some advanced cases you may want to change the host as well, but those will not be described here.
- __session_data_root__: New session directories will be created under this directory. It is outside the repository by default so you will probably want to change it. Note that the attribute value must be a python `pathlib.Path` object.
- __media_dir__: This is where videos and images are saved when there is no open session. It is also outside the repository by default. Again, the value of the attribute must be a python `pathlib.Path` object.
- __archive_dirs__: Here you can setup archive locations. The UI supports copying existing sessions into these archive directories to easily backup your data. The default values are just examples and should probably be changed.
- __mqtt__: The MQTT broker server host and port number. You might need to change this as well, depending on your MQTT broker setup.

## Running ReptiLearn

The ReptiLearn system is made of three parts: 
- Main system in the `system` directory
- Web server running the user interface in the `ui` directory
- Arena hardware control in the `arena` directory (optional)
Each of these needs to be run independently

To run ReptiLearn follow these steps:
1. Run the MQTT broker (refer to the documentation of the MQTT broker you installed previously)
2. Run the database (optional)
3. Open a terminal (Anaconda powershell prompt on windows) and go to the directory where the repository was cloned
4. Activate the anaconda environment we created during installation:
```bash
conda activate reptilearn
```

4. Start the ReptiLearn system:
```bash
cd system
python main.py
```

OR if you want to use a different config module than the default (the default is at system/config/config.py):

```bash
cd system
python main.py --config config-module
```
where `config-module` is the name of a python module inside the `config` directory without the .py extension.
For example, ```python main.py --config config2``` will start the system configured according to `config/config2.py`.

5. Start the UI server. Open a new terminal, go to the repository directory, and enter:
```bash
cd ui
npm start
``` 

To use a different network port for the server you should define a PORT environment variable with the required value. On POSIX systems such as linux or macOS this can be achieved easily by using the following command instead of the one above:

```bash
cd ui
PORT=3001 npm start
```

6. Start the Arena MQTT-Serial bridge (optional). From another terminal window go again to the repository directory and enter:
```bash
conda activate reptilearn
cd arena
python arena.py
```

OR if you want to use a different config module than the default (the default is at arena/config.py):

```bash
conda activate reptilearn
cd arena
python arena.py --config config-module
```

where `config-module` is the name of a python module containing the config values without the .py extension.

NOTE: Using the Arena MQTT-Serial bridge to communicate with Arduino boards requires additional configuration and setup. Please refer to the [MQTT-Serial bridge documentation](mqtt_serial_bridge.md) for more information.

7. Open a recent version of a modern web browser and point it to the address of the UI server. This would be `http://localhost:3000` by default. If you started the server using another port in step 5, use that port instead of 3000.