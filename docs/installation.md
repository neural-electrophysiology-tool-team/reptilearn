# Installation

## Prerequisites

ReptiLearn was mostly tested on Ubuntu 20.04 but also works on MacOS, Windows, and probably other linux distributions.

Before starting, it's necessary to first install the following software:

- [Anaconda](https://www.anaconda.com/)
- [Git](https://git-scm.com/downloads)
- [Node.js](https://nodejs.org/en/)
- an MQTT Broker such as [Eclipse Mosquitto](https://mosquitto.org/)

## Installation

1. Open a terminal (git bash on windows) and run:
 
 ```bash
 git clone https://github.com/neural-electrophysiology-tool-team/reptilearn
 ```
 
2. Next create an Anaconda environment by running the following commands in the terminal (on Windows first open an Anaconda Prompt in the repository directory):

```bash
cd reptilearn
conda env create -f environment.yaml
```

3. Install the Web-UI node.js dependencies:
```bash
cd ui
npm install
cd ..
```

## Database installation (optional)

The system can optionally be used to log data in a [TimescaleDB](https://www.timescale.com/) database. To use this feature, you first need to install the database (see the link above for information). [Docker image installation](https://docs.timescale.com/install/latest/installation-docker/) is recommended. 

Next, install the [psycopg2](https://pypi.org/project/psycopg2/) library into the anaconda environment you created previously:

```bash
conda activate reptilearn
pip install psycopg2
```

Lastly, you need to create a new database. This can be done by running the SQL command (this can be done using [psql](https://www.postgresql.org/docs/current/app-psql.html)): 
```sql 
CREATE DATABASE reptilearn;
```

## Configuration files

The system uses a number of configuration files: 

- Main system configuration at [system/config/config.py](/system/config/config.py)
- Arena interfaces configuration at [system/config/arena_config.json](/system/config/arena_config.json)
- Arena MQTT-Serial bridge configuration at [arena/config.py](/arena/config.py) (see [arena](/arena) for more information about the last two)

Before running ReptiLearn you should probably change some values in the main config file, including `session_data_root` and `media_dir`. See the [user guide](user_guide.md) for more information.

## FFmpeg setup

The system uses [FFmpeg](https://ffmpeg.org/) to encode video files. Normally it should be installed when creating the anaconda environment, however if you want to use a different version (for example one that supports GPU encoding), create the file `system/.env` with the following content:

```
IMAGEIO_FFMPEG_EXE=/path/to/ffmpeg/executable
```

For information about running and using the system head over to the [user guide](user_guide.md).