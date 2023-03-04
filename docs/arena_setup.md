# Setting up the arena controller

ReptiLearn can control and monitor various electronic devices by communicating with [Arduino boards](https://www.arduino.cc/). Some examples include lights, cue LEDs, temperature sensors, reward feeders, and camera triggers. 

You can connect any number of devices to one or multiple Arduino boards, and control all of them without having to write any Arduino code. This is accomplished by using a single Arduino program that can interface with a number of different types of components. Each Arduino board is automatically programmed with the same generic program, and once communication between the board and computer software is established, each board is configured based on its individual settings.

## The arena controller

Communication with, and programming of the boards is handled by the Arena controller ([arena.py](../arena/arena.py)). The ReptiLearn software communicates with the controller using the [MQTT](https://mqtt.org/) protocol. The controller provides bi-directional communication between MQTT clients and connected Arduino boards.

By default, ReptiLearn will start the arena controller as a sub-process when it starts up, unless the arena config file is empty. It's also possible to run the controller separately, or even on a different computer. See [here](#run-arena-controller-separately) for more information. In the rest of the document it's assumed you're running the controller as a sub-process.

## Supported Arduino boards

The arena controller should work with any Arduino board that has at least 48KB of program memory and 4KB of RAM. Check your model specifications. At the time of writing, most available boards do not have enough memory. We used Arduino Nano Every boards which work well and are relatively low cost.

## Configuring the arena controller

The arena config file is stored by default in `reptilearn/system/config/arena_config.json`. To make changes you can use the arena settings dialog:

- Run ReptiLearn
- Open the ReptiLearn web app in a browser
- Open the Arena menu by clicking the button
- Click on "Arena settings" to open the settings dialog

### Adding Arduino boards

- Connect an Arduino board
- In the settings dialog, click the plus (+) button
- You should be able to select the port of the board in the dialog that opens.
- Choose a name for this Arduino, and fill in the FQBN of your board (see below).
- Click the add button
- The new board configuration should appear. 
- Click on the save button to save the new config file.

### Fully qualified board name (FQBN)

The FQBN string identifies the Arduino board type, and is necessary for uploading programs to the Arduino. To find the FQBN of your board run:

```bash
arduino-cli board listall
```

For example for __Arduio Nano Every__ the FQBN is `arduino:megaavr:nona4809`.

### Uploading the program

After you saved the arena configuration you can upload the program to the Arduino board you added:

- Open the "Arena settings" again
- Choose the new board from the board list (according to the name you chose when you added it)
- Click on "Upload program"

The upload process should begin and you should see messages in the log.

### Not enough memory error
As mentioned above, many Arduino boards do not have enough memory to store the arena program and run it. If you use one of these boards you will encounter a "not enough memory" error while trying to upload.

In most cases getting a supported board model should solve this problem, however it's also possible to reduce the storage space requirements of the program by removing unnecessary interface types from the source code. To do that, open [arena/arduino_arena/arduino_arena.ino](../arena/arduino_arena/arduino_arena.ino), and comment out any of the lines that start with `#include` for interfaces that you don't need. See the comment in the includes section of the .ino file.

### Connecting multiple boards

You can repeat the previous steps with any number of additional Arduino boards. It is recommended to connect the boards one-by-one, to make them easier to identify.

### Adding interfaces

After adding an arduino board you need to configure its interfaces. These define which devices are connected to the board and their parameters, including how they will appear in the Arena menu. 

You can configure interfaces in the "Arena settings" dialog. After choosing the Arduino board you want to configure, the interfaces array should show up in the configuration editor. As a simple example, edit your config to look like this:

```json
{
    "serial_number": "<board serial>",
    "fqbn": "<board fqbn>",
    "interfaces": [
        {
            "name": "LED",
            "pin": 13,
            "type": "line",
            "ui": "toggle"
        }
    ]
}
```

Then click the save button, and if the arena controller wasn't already running, open the Arena menu and click "Start arena".

Assuming all went well, the controller should now run and the new interface should appear in the Arena menu. Clicking on the interface button (labeled LED with a toggle icon) should turn on the LED.

See [here](arena_interfaces.md) For more information about interfaces.

NOTE: Some boards have a built-in LED connected to pin 13. If that's not the case for your board, you can connect one between pin 13 and the ground pin of the board (if needed use an appropriate resistor in serial with the LED). 

### Allow get

The system periodically polls each board for its current state (every minute by default). It also requests the value of each interface after sending it a command. This might take some time and prevent the board from doing other things, therefore it should be avoided for time-sensitive functions (such as the camera trigger).

The `allow_get` board parameter can be set to `false` in the arena config in order to prevent sending these state updates. 

## Arena menu

The Arena menu in the web app lets you manually send commands and monitor sensors, as well as stop and re/start the arena controller. Each interface is displayed in the menu according to its configuration. The "Poll arena" button will request each board for its current state and update the menu and system state accordingly.


## Run the arena controller separately

The arena controller can be run as a separate program instead of as a sub-process of the main system. This allows running the controller on a different computer. In this case it's not possible to program the boards or start and stop the controller from the ReptiLearn web app.

To run the controller on another computer, download and install reptilearn as described [here](getting_started.md#installation) on both computers. Make sure to install [Arduino-CLI](getting_started.md#arduino-cli-optional) on the computer that will run the arena controller.

To prevent ReptiLearn from running the controller on startup open your config file and set the `run_controller` attribute in the arena dictionary to False. For example:

```python
arena = {
    "run_controller": False,
}
```

Restart ReptiLearn if it's already running for the change to have effect.

### Configuration

Here we assume you are running the controller from the same ReptiLearn installation as the ReptiLearn system. See more information [below](#running-remotely) if you want to  run it remotely.

#### Adding boards

When running the controller separately it's not possible to find available boards in the "Add Arduino" dialog, as before. To find the serial number of your arduino, open a terminal pointing to the reptilearn directory (use Anaconda prompt on windows), and run the controller with the `--list-ports` argument:

```bash
cd arena
conda activate reptilearn
python arena.py --list-ports
```

You should see a list of all available serial ports with their serial numbers. Find the FQBN of your board with `arduino-cli` as explained [above](#fully-qualified-board-name-fqbn).

### Uploading the program

After configuring the boards in "Arena settings", use the controller again to upload the program. Upload to all configured boards by running:

```bash
cd arena
conda activate reptilearn
python arena.py --upload
```

To upload to a specific board run:

```bash
python arena.py --upload <board_name>
```

Where <board_name> is the name that was chosen when configuring the board.

### Running the controller

To run the controller open a terminal (Anaconda prompt in Windows) window pointing to the reptilearn directory, and run:

```bash
cd arena
conda activate reptilearn
python arena.py
```

OR if you want to use a different config module than the default (the default is at arena/config.py):

```bash
conda activate reptilearn
cd arena
python arena.py --config config-module
```

where `config-module` is the name of a python module containing the config values without the .py extension.

Once the board is running, log messages should appear in the ReptiLearn web app, and the Arena menu should show the configured interfaces.

Press Ctrl-C to stop the controller.

### Running remotely

When running the controller on a different computer its necessary to set the same MQTT broker host and port, in both the ReptiLearn config file, and the controller config file at [arena/config.py](arena/config.py). See [here](getting_started.md#remote-mqtt-broker) for more information on using a remote MQTT broker.

Both installations should also have a copy of your `arena_config.json` file. This is the file that is edited using the "Arena settings" dialog. You can usually find it at `system/config/arena_config.json`, but you can change its location by editing `arena_config_path` in both config files.

After doing the previous steps, you can run both ReptiLearn and the arena controller as described above. They should be able to communicate with each other through the MQTT broker.
