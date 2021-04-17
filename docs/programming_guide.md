# Experiment Programming Guide

## Starting the system

To start the system change to the `./system` directory and run `python main.py`. The system configuration is stored in a python module inside the system/config directory. The --config argument can be used to specify a custom config module, otherwise, the config/config.py module is used by default.

## Creating a new experiment module

To create a new experiment type create a new python module file and save it in the experiments modules directory (as specified by the `experiment_modules_dir` attribute in the configuration file, `<reptilearn root>/system/experiments/` by default). The module should contain a single subclass of the experiment.Experiment class.

## Loading an experiment

Once the file is created, click on the “Refresh list” option under the experiment list dropdown in the web-ui. The experiment name should now appear on the list. Selecting it will set the current experiment to the newly created one.

To update the code of a loaded experiment, save your code changes and click the “Reload” button.

## Experiment lifecycle

An experiment goes through several lifecycle events, each event invokes a method of the experiment class which was defined in the experiment module:

- `setup(self)`: called when the experiment is loaded.
- `run(self, params)`: called when the experiment starts, usually by pressing the “Run” button.
- `end(self, params)`: called when the experiment ends, either by pressing the “End” button, or when all experiment phases have finished (see below)
- `release(self)`: called when the experiment is unloaded (another experiment is loaded, the system shuts down, etc.).

Experiments can have a number of phases - trials and blocks. Blocks can have distinct parameters (see experiment parameters below), and may contain any number of trials sharing the same parameters. The current block and trial are stored in the state path `(“experiment”, “cur_block”)` and `(“experiment”, “cur_trial”)` respectively (see system state below).

When running an experiment, the first block and trial start running (this might change in the future).
The experiment class has the following method hooks for blocks and trials:

- `run_block(self, params)`: called when a block starts.
- `end_block(self, params)`: called when a block ends.
- `run_trial(self, params)`: called when a trial starts.
- `end_trial(self, params)`: called when a trial ends.

When loading an experiment its blocks will show up below the experiment parameters. Blocks can be added, removed, duplicated, or shuffled around, using the buttons in the block section in the web-ui.

Once an experiment is running, it is possible to move to the next block or trial manually by pressing the plus buttons below the experiment bar, or by calling the `experiment.next_block()` and `experiment.next_trial()` functions.

## Experiment parameters

An experiment can have customizable parameters that can be assigned using the web-ui. Any parameter can be added, however usually experiments define default parameter names and values as described below. These will show up in the web-ui after loading the experiment (or after pressing the “Reset” button). In addition, each block can define additional parameters as well as override experiment parameter values.
The parameters are passed as an argument to each lifecycle method. run() and end() receive the experiment parameters as a dictionary, and `run_trial()`, `end_trial(), run_block()`, and `end_trial()` receive the relevant parameters for the current block - the experiment parameters are overridden with values defined in the block parameters.

### Defining default parameters and block parameters

To define default experiment parameters add a dictionary as a `default_params` class attribute to the experiment class. To define default blocks and block parameters add a `default_blocks` list in which each element is a dictionary containing default block parameters. For example:

```python
class MyExperiment(experiment.Experiment):
    default_params = {
            "param1": param1-value,
	            "param2": param2-value,
		            ...
	}

    default_blocks = [
            {"param1": overridden-param1-value, "param3": some-value},
	            {"param2": overridden-param2-value, "param4": some-value},
	]
```

This code will define an experiment with some default parameters, and two default blocks, each overriding one parameter and defining another default block parameter.

### Built-in parameters (could change in the future)

Some parameters have a special meaning for the system:
- num_trials: determines the number of trials for each block. This can be either an experiment parameter or defined individually for each block. When this parameter is defined, once this number of trials are executed the block will end, moving to the next block or ending the experiment if the current block is the last one.

## System state

The system maintains a global synchronized state using the state module. The state is a nested dictionary structure that can be shared between processes (see multiprocessing below), and contain the current state of the system. The state can be accessed using state.Cursor objects, and callback can be added to listen for updates of specific state values. See the documentation of the state module for more information.
The current state of the system is shown in the web-ui in the state section (under the experiment section).

## Data collection and storage

Whenever an experiment is starting, a data directory is created for it under the experiment data root directory (determined by the `exepriment_data_root` config attribute). The directory name is based on the experiment id (which can be set in the web-ui), and it's stored in the state path `("experiment", "data_dir")`.

Once the directory was created, any data will be stored inside it. This could include recorded videos and images, the log file (`experiment.log`), the event log and any other data logs (see below).

### Logging

The experiment class provides a python logger object (self.log). Messages sent to this logger will appear in the web-ui and saved to the experiment log file.

### Data logs

Time series data that's collected during the experiment can be stored to csv files and/or to the database using a data logger. The `data_log.QueuedDataLogger` class, a subclass of `data_log.DataLogger`, provides a simple mechanism for defining data tables, and adding rows of data. See the `data_log.py` documentation for more information.

### Event log

The event log is a special DataLogger that can be used to automatically log an event whenever specific state paths are updated, or when mqtt messages are published on specific topics. It is configured in the `event_log` dictionary of the config module, and default events that should always be recorded are defined there. The event log is created when the experiment starts (before calling its `run` method), and the logger can be accessed through the module attribute `experiment.event_logger`. Once the event log was created, events can be added or removed. Custom events can be logged by calling the `log` method. See the `event_log.py` documentation for more information.

### Video recordings and snapshots

Synchronized video recording from multiple image sources (see below) is handled by the `video_record` module. The recorder can be configured under the `video_record` config attribute. To start and stop recording use the `video_record.start_record` and `stop_record` functions. Image sources can be selected from the web-ui, by explicitly listing them in `start_record` or by using `video_record.set_selected_sources`, `video_record.select_source`, or `video_record.unselect_source`. 
If the cameras are configured to synchornize with a ttl trigger, it can be started and stopped using `video_record.start_trigger`, and `video_record.stop_strigger`, or by clicking the trigger button in the web-ui. When the trigger is already running before starting a recording, it will automatically pause, and start once the recording starts. 

To take a single snapshot of the current image for each selected image source use `video_record.save_image`. A single image for each source will be saved in the experiment data directory.

The current state of the video recorder can be accessed under the `("video_record")` state path.

For more information see the video_record module documentation.

## Controlling the arena 

The arena module provides functions for controlling the arena hardware. It also listens for sensor reading, and stores them, together with the state of the various components under the `"arena"` state path. The arena can also be controlled from the Arena menu in the web-ui top panel. See the arena module documentation for more information.

## MQTT client

Communication with image observers and programs running on the touchscreen is handled through the MQTT protocol. The mqtt module provides a client running on the main process which can be accessed through the `mqtt.client` module attribute. See the mqtt.MQTTClient documentation for more information.

## Scheduling

The schedule module provides a number of functions for running tasks on various time schedules. See the documentation for more information.

## Image Sources and Image Observers

The processing and analysis of image data is done by `ImageSource` and `ImageObserver` classes. ImageSources run as separate processes and acquire a stream of images from some source (such as a camera). The image data is stored in a shared memory that can then be accessed by any number of ImageObservers. ImageSources are defined in the image_sources config module dict. The dict keys are the image source ids, and are used for selecting record sources, and defining ImageObservers.

ImageObservers also run on separate processes. They are attached to specific ImageSources and are notified by the source when new image data is available. Observers can communicate with the experiment (running on the main process) through MQTT (usually when dealing with large amounts of data, such as the bounding box coordinates of the animal for each frame), or by updating the central state. State updates should be regarded as slow, since each update and access effectively make a copy of the entire state.

The observers are defined under the image_observers dict in the config module. The observer instances are stored in a dict that can be accessed through the `experiment.image_observers` module attribute. Both dicts use keys as they are defined in the configuration. The observers and their processes are all created on system startup, however they wait and do nothing until receiving a start message. To start and stop an observer invoke its `start_observing` and `stop_observing` methods respectively.

The video_stream module is responsible for image sources and observers functionality, and the base classes defined there can be subclassed to create new source and observer classes.

## Accessing config attributes

Since the config module is selected dynamically at system startup, it should only be accessed by using the `experiment.config` module attribute. This holds a reference to the config module that is being used.
