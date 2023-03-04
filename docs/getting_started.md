# Getting started

## Installation

The software was mostly tested on Ubuntu 20.04, but also works on MacOS, Windows, and probably other linux distributions (although some features might not work).

Follow these steps to install:

### Download

- Install [Git](https://git-scm.com/downloads)

- Open a terminal (git bash on windows), change the directory to where you want to install, and run:
 
 ```bash
 git clone https://github.com/neural-electrophysiology-tool-team/reptilearn
 ```

### Setup Python environment

- Install [Anaconda](https://www.anaconda.com/)

- Run the following from the same directory to create a reptilearn Python environment (on Windows use Anaconda Prompt):

```bash
cd reptilearn
conda env create -f environment.yaml
```

This should install all the necessary Python dependencies.

### Build the UI webapp

- Install [Node.js](https://nodejs.org/en/)

- Run the following in a terminal window pointing to the `reptilearn` directory to install node.js dependencies and build the webapp:

```bash
cd ui
npm install
npm run build
cd ..
```

### MQTT broker (optional)

Communication with Arena hardware and other software components (e.g. touchscreen apps) is done using the [MQTT](https://mqtt.org/) protocol. When starting up ReptiLearn it tries to connect to an MQTT broker running on the same machine on the default MQTT port (1883). If a connection was not successful you will see an error message, but other parts of the system can still be used.

We recommend installing [Eclipse Mosquitto](https://mosquitto.org/). To use a broker running on a different machine see [Remote MQTT broker](#remote-mqtt-broker) below for more information.

NOTE: ReptiLearn doesn't currently support non-anonymous access to the MQTT broker. If you're using Eclipse Mosquitto and have problem connecting (connection refused), add the following line to your mosquitto.conf file:

```
allow_anonymous true
```

### Arduino-CLI (optional)

For programming Arduino boards you need to install [arduino-cli](https://arduino.github.io/arduino-cli/latest/installation/).

Once installed, run these commands to install the necessary Arduino libraries:
```
arduino-cli core update-index
arduino-cli lib install AccelStepper ArduinoJson OneWire DallasTemperature
```

Finally, install the software for your specific Arduino board model(s). For example for an Arduino Nano Every or UNO WiFi Rev 2 run:
```
arduino-cli core install arduino:megaavr
```

For other models, the following command will list all available board IDs:
```
arduino-cli core list --all 
```

When you have your board ID, install the core for it using this command:
```
arduino-cli core install <board ID>
```

Repeat this for each type of board you intend to use.

### FFmpeg setup (optional)

[FFmpeg](https://ffmpeg.org/) is used to encode video files. Normally it should be installed together with the ImageIO library when creating the anaconda environment, however if you want to use a different installed version (for example one that supports encoding on a GPU), create the file `reptilearn/system/.env` with the following content:

```
IMAGEIO_FFMPEG_EXE=/path/to/ffmpeg/executable
```

## Configuration

The system uses python modules as configuration files. The default configuration can be found at [system/config/config.py](/system/config/config.py). You would probably want to make some changes before running for the first time. It's possible to make changes directly in the default config file, but we recommend creating a new config file (e.g. system/config/my_config.py). 

Any values not defined in the new config file will be taken from the default config file. To use the new config, run with a `--config my_config` command line argument (see [Running](#running) below).

For example, this is how a config file that only changes the web server port value would look like:
```python
web_ui = {
    "port": 3501,
}
```

You probably want to change the directories for storing data:

- `session_data_root`: This is where session data will be stored (each session is stored in its own subdirectory)
- `media_dir`: Videos and images are stored here when there's no open session

Make sure these directories exist before running.

## Running

- If you're using a local MQTT broker, make sure it's running
- In a terminal (Anaconda Prompt on Windows) switch to the installation directory and run:

```
cd system
conda activate reptilearn
python main.py
```

OR if you want to use a different config module:

```
cd system
conda activate reptilearn
python main.py --config my_config
```

where `my_config` is the name of a python module inside the `config` directory without the .py extension.
For example, ```python main.py --config config2``` will start the system configured according to `system/config/config2.py`.

- Open a recent version of your favorite web browser, and go to [`http://localhost:3500`](http://localhost:3500). You can access the web app remotely by using an ssh tunnel or by using the computer's IP address instead of `localhost`.

NOTE: We recommend using ssh tunnels and/or a VPN to securely access the web app. ReptiLearn has no support for user authentication or any other security measures.

## Database

A [TimescaleDB](https://www.timescale.com/) database can optionally be used to store log data. To use this feature, you first need to install the database (see the link above for information). [Docker image installation](https://docs.timescale.com/install/latest/installation-docker/) is recommended. 

If you use the Docker image, you must also install [`psql`](https://www.timescale.com/blog/how-to-install-psql-on-mac-ubuntu-debian-windows/) separately.

Once `psql` is installed, install the [psycopg2](https://pypi.org/project/psycopg2/) library into the anaconda environment you created previously:

```bash
conda activate reptilearn
pip install psycopg2
```

Lastly, you need to create a new database. This can be done by running the SQL command (this can be done using [psql](https://www.postgresql.org/docs/current/app-psql.html)): 
```sql 
CREATE DATABASE reptilearn;
```

## Real-time object detection using YOLOv4

ReptiLearn currently supports real-time object detection using the YOLOv4 neural network model. YOLO can be used to obtain bounding boxes of relevant objects in image streams (such as your subject animals). We use the original darknet version from [this](https://github.com/AlexeyAB/darknet) repository. Darknet requires a CUDA capable GPU, and working installations of NVIDIA CUDA, and cuDNN.

First, configure your cameras or other image sources (see [Camera configuration](docs/camera_config.md) for more information), then follow these steps to setup the model:

- [Compile darknet](https://github.com/AlexeyAB/darknet#how-to-compile-on-linux-using-make). We recommend using the `make` method. Make sure to set `LIBSO=1` in the `Makefile` to compile into a static library.

- Copy the compiled library `libdarknet.so` from the YOLOv4 directory into `reptilearn/system/image_observers/YOLOv4`

- Generate/copy model weights and configuration: To train the model to detect your custom objects follow this [section](https://github.com/AlexeyAB/darknet#how-to-train-to-detect-your-custom-objects) in the darknet documentation. Another option is to use pre-trained weights. In either case you should end up with three files: A `.cfg` file containing your network configuration, an `obj.names` file containing a list of object classes, and a `.weight` file containing the trained model weights. Copy these files into `reptilearn/system/image_observers/YOLOv4`.

- Add the YOLOv4 image observer: In the ReptiLearn web app, open the `Video` menu and click on `Video settings`. Switch to the `Observers` tab, and click the + (plus) button. Choose the class `yolo_bbox_detector.YOLOv4ImageObserver` and enter a descriptive id. A new image observer should be added, and its default parameters should be displayed in the settings window. 

- Configure the image observer. Assuming you copied the model files according to the step above, edit the following observer parameters:
    - `cfg_path`: set to `image_observers/YOLOv4/<your .cfg file name>`
    - `weights_path`: set to `image_observers/YOLOv4/<your .weight file name>`
    - `src_id`: The id of the image source you want this observer to analyze 
    - Additional parameters you may want to change are:
        - conf_thres: Detections with lower confidence than this value will be ignored
        - nms_thres: Threshold for the non-max suppression algorithm. 

- Click the `Apply & Restart` button to restart the video system and load the new observer.

Assuming everything worked, the YOLOv4 model should now be loaded and you should see a log message in the web app. If you don't see any message, check the terminal window where ReptiLearn is running for any errors coming from the YOLO model. 

NOTE: To use the detection data in real-time or store it you need to run the appropriate experiment. See [Programming experiments](docs/programming_experiments.md) for information about interfacing with image observers.

see [Extending the video system](docs/programming_video_system.md) for information about adding support for additional models.

## Remote MQTT broker

ReptiLearn can be configured to use a remote MQTT broker. To do so, edit your config file and change the `host` value of the `mqtt` dictionary. You may also need to change the `port` value if the remote broker uses a different port.

```python
# MQTT server address
mqtt = {
    "host": "<remote MQTT broker host name>",
    "port": <remote broker port number>,
}
```

You will also need to change these values in the arena controller configuration file at `reptilearn/arena/config.py`:

```python
# MQTT settings
mqtt = {
    # Server host and port number
    "host": "<remote MQTT broker host name>",
    "port": <remote broker port number>,

    ...
}
```

After restarting ReptiLearn it should use the new broker configuration.
