# Experiment Programming Guide

## Creating a new experiment module

To create a new experiment type create a new python module file and save it in the experiments modules directory (as specified by the experiment_modules_dir attribute in the configuration file, `<reptilearn root>/system/experiments/` by default). The module should contain a single subclass of the experiment.Experiment class.

## Loading an experiment

Once the file is created, click on the “Refresh list” option under the experiment list dropdown in the web-ui. The experiment name should now appear on the list. Selecting it will set the current experiment to the newly created one.

To update the code of a loaded experiment, save your code changes and click the “Reload” button.

## Experiment lifecycle

An experiment goes through several lifecycle events, each event invokes a method of the experiment class:

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

Once an experiment is running, it is possible to move to the next block or trial manually by pressing the plus buttons below the experiment bar, or by calling the experiment.next_block() and experiment.next_trial() functions.

## Experiment parameters

An experiment can have customizable parameters that can be assigned using the web-ui. Any parameter can be added, however usually experiments define default parameter names and values as described below. These will show up in the web-ui after loading the experiment (or after pressing the “Reset” button). In addition, each block can define additional parameters as well as override experiment parameter values.
The parameters are passed as an argument to each lifecycle method. run() and end() receive the experiment parameters as a dictionary, and `run_trial()`, `end_trial(), run_block()`, and `end_trial()` receive the relevant parameters for the current block - the experiment parameters are overridden with values defined in the block parameters.

### Defining default parameters and block parameters

To define default experiment parameters add a dictionary as a `default_params` class attribute to the experiment class. To define default blocks and block parameters add a `default_blocks` list in which each element is a dictionary containing default block parameters. For example:

```python
class MyExperiment(experiment.Experiment):
    default_params = {
            “param1”: param1-value,
	            “param2”: param2-value,
		            ...
			        }

    default_blocks = [
            {“param1”: overridden-param1-value, “param3”: some-value},
	            {“param2”: overridden-param2-value, “param4”: some-value},
		        ]
```

This code will define an experiment with two default parameters, and two default blocks, each overriding one parameter and defining another default block parameter.

### Builtin parameters (could change in the future)

Some parameters have special meaning for the system:
num_trials: determines the number of trials for each block. This can be either an experiment parameter or defined individually for each block. When this parameter is defined, once this number of trials are executed the block will end, moving to the next block or ending the experiment if the current block is the last one.

## System state

The system maintains a global synchronized state using the state module. The state is a nested dictionary structure that can be shared between processes (see multiprocessing below), and contain the current state of the system. The state can be accessed using state.Cursor objects, and callback can be added to listen for updates of specific state values. See the documentation of the state module for more information.
The current state of the system is shown in the web-ui in the state section (under the experiment section).

## Logging

The experiment class provides a logger object (self.log). Messages sent to this logger will appear in the web-ui and experiment log files.

## System API

Following is a brief description of the various modules that are used for interacting with the system. See the documentation and source code of each module for more information.

- experiment:
- state:
- video_record:
- data_log:
- event_log:
- mqtt:
- schedule:
- arena

## Image Sources and Image Observers

## Configuration modules
