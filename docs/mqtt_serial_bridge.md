# Control arena hardware using ReptiLearn and the MQTT-Serial bridge

The ReptiLearn system can control and monitor various electronic devices by communicating with any number of Arduino boards. Some examples include lights, cue LEDS, temperature sensors, reward feeders, and camera triggers. 

It's possible to control custom hardware configurations that fit your specific needs without writing a single line of Arduino code. This is accomplished by using a single Arduino program that can interface with any number of different components. Each Arduino board is automatically programmed with the same generic program, and once communication between the board and the computer software is established, each board is configured based on its individual settings.

Communication with, and programming of the boards is handled by the [arena.py](../arena/arena.py) program in the arena directory of the ReptiLearn repository. The main ReptiLearn system communicates with `arena.py` using the [MQTT protocol](https://mqtt.org/) using a specific message format. In turn `arena.py` contains an MQTT-Serial bridge that provides bi-directional message routing between MQTT and connected Arduino boards that are running the generic program. 

The ReptiLearn system can send commands to individual interfaces on individual boards and get back the interfaces current values. The system can also poll every board for its current state. This is usually done once a minute, but can be changed in the main ReptiLearn config file. In addition, the bridge can also send log messages and errors from the Arduino boards to the ReptiLearn log.

Setting up the hardware requires first identifying each individual board, and then configuring the various interfaces (i.e. electronic devices) you want to use. This is currently done by modifying two configuration files, as explained below.

# Supported Arduino boards

The MQTT-Serial bridge should work with any Arduino board that has at least 48KB of program memory and 4KB of RAM. Check your model specifications. At the time of writing, most available boards do not have enough memory. We used Arduino Nano Every boards which work well and are relatively low cost.

# Installation

First, follow the ReptiLearn [installation instructions](installation.md) if you haven't done so yet. 

## `arduino-cli`

For programming the Arduino boards you need to install
[arduino-cli](https://arduino.github.io/arduino-cli/latest/installation/).

Once installed, run these commands to install the necessary Arduino libraries:
```
arduino-cli core update-index
arduino-cli lib install AccelStepper
arduino-cli lib install ArduinoJson
arduino-cli lib install OneWire
```

Finally, install the software for your specific Arduino board model. For example for an Arduino Nano Every or UNO WiFi Rev 2 run:
```
arduino-cli core install arduino:megaavr
```

For other models, the following command will list all available board IDs:
```
arduino-cli core list --all 
```

When you have your board ID, install the core for it with this command:
```
arduino-cli core install <board ID>
```

# Configuration

The arena program configuration file can be found in [arena/config.py](../arena/config.py). Open the file in a text editor.

## Identifying and configuring Arduino boards
To configure individual Arduino boards you need to identify them by their `hwid` string and set their `fqbn` board id.

Open a terminal and point it to the repilearn repository directory (use Anaconda powershell on Windows). Switch to the reptilearn anaconda environment (e.g. `conda activate reptilearn`) and run:
```
python arena.py --list-ports
```
The output should look something like this (if you have any boards already connected):
```
Available serial ports:

        /dev/cu.Bluetooth-Incoming-Port: n/a, hwid="n/a"
        /dev/cu.usbserial-A800eFFZ: FT232R USB UART, hwid="USB VID:PID=0403:6001 SER=A800eFFZ LOCATION=1-1.2"
```
Connect each of the Arduino boards you plan to use, one by one, run the command again for each one, and write down their `hwid` string. 

We also need the `fqbn` identifier of each board. To find it run:
```
arduino-cli board listall
```
For example for Arduio Nano Every the `fqbn` is `arduino:megaavr:nona4809`.
Add this information to the ports dictionary in the config file. For each arduino board, add a port dictionary like so:

```python
...
serial = {
    "ports": {
        "<port name>": {
            "id": "<hwid>",
            "fqbn": "<arduino FQBN>"
        },
        "<another port name>": {
            "id": "<hwid>",
            "fqbn": "<fqbn>"
        },

        # The camera trigger port and other time sensitive boards should disallow get commands, for example:
        "camera_trigger": {
            "id": "<hwid>",
            "fqbn": "<fqbn>",
            "allow_get": False,
        }
    },
}
...
```
The `"allow_get"` attribute determines whether get commands will be passed to this board or not. The `get` command causes the board to send its current state. This might take some time, and so should be avoided for time-sensitive functions, such as the camera trigger.

## MQTT
You may want to change the host and port settings of the MQTT broker. The default values assume the broker is on the same machine and uses the default port 1883. 

It's also possible to change the MQTT topics used to receive commands and publish serial data.

# Uploading the Arduino program

The last setup step is to program the Arduino boards. Once all the boards are configured with correct `hwid` and `fqbn` values, connect all of them and run:
```
python arena.py --upload
```
This will upload the program to every board defined in the configuration file.

## Not enough memory error
As mentioned above, many Arduino boards do not have enough memory to store the arena program and run it. If you use one of these boards you will encounter a "not enough memory" error while trying to upload.

In most cases getting a supported board model should solve this problem, however it's also possible to reduce the storage space requirements of the program by removing unnecessary interface types from the source code. To do that, open [arena/arduino_arena/arduino_arena.ino](../arena/arduino_arena/arduino_arena.ino), and comment out any of the lines that start with `#include` for interfaces that you don't need. See the comment in the includes section of the .ino file.

# Configuring interfaces

The Arduino program can interface with different electronic devices. The file [system/config/arena_config.json](../system/config/arena_config.json) defines which interfaces will be used with each Arduino board. It uses the JSON format. Unfortunately, you have to edit it by hand. The basic structure is an object with a key for each arduino. The keys should be the same as the ones you used in the arena config.py file. 

For example, a setup with two boards, one for controlling two LEDs, and one to trigger the cameras could look like this:

```json
{
  "arena": [
    {
        "name": "LED1",
        "type": "line",
        "pin": 10,
        "ui": "toggle"
    },
    {
        "name": "LED2",
        "type": "line",
        "pin": 11,
        "ui": "toggle"
    }
  ],
  "camera_trigger": [
    {
        "name": "Camera Trigger",
        "type": "trigger",
        "pin": 12,
        "pulse_len": 17,
        "pulse_width": 0.7,
        "ui": "camera_trigger"
    }
  ]
}
```
Each board has its own array of interface objects. Each interface has various properties that can be configured. 

Here, LED1 uses digital pin 11 and LED2 uses digital pin 12. The camera trigger `trigger` interface will send a pulse every 17ms on digital pin 12.

More information about the various interfaces can be found below in the interface documentation section.

# Running the MQTT-Serial bridge

Once everything is configured you can run the bridge. Follow the instruction in the [user guide](user_guide.md) on how to run all parts of the system. Pressing Ctrl-C should stop the bridge.

When the bridge is starting up the Arduino boards should send setup requests and you should see messages in the ReptiLearn log detailing the connected interfaces. If everything went well you should see your interfaces in this list. The arena menu in the ReptiLearn UI should also show and allow you to control the defined interfaces.

# Interface documentation

This section describes the available interface types and their configuration attributes.

## Common interface attributes

- name: Interface name for identification. NOTE: Interface names should be unique across all connected boards.
- type: The interface type. Currently one of `line trigger feeder dallas_temperature`. Each one is explained below.
- ui: Determines how this interface is controlled in the ReptiLearn user interface.

## Interface types and attributes
There are a number of supported interfaces. The `"type"` attribute determines which one is used.

### `line`
Control a single digital output pin. Useful for turning things on and off.

Attributes:
- `pin`: Integer. The Arduino digital pin number to use.
- `reverse`: true | false. Reverse the line output. Will output HIGH when its  state is 0 and LOW when it is 1. 

Commands:
- `get`: Sends back the current state of the line - 0 or 1.
- `toggle`: Set the line state to the opposite of the current one.
- `set <x>`: Set the line state to <x> (0 or 1)
- `periodic <0|1> <period_dur>`: Control toggling the line on and off at a fixed rate. For example `periodic 1 500` will start toggling every 500 ms. `periodic 0` will stop the toggling. The period can be reliably timed at quite short durations. This is useful for blinking LEDs, etc.

Example:
```json
{
    "name": "LED",
    "type": "line",
    "pin": 12,
    "ui": "toggle"
},
```

### `trigger`
Output pulses at a fixed frequency on a single pin. This is used for synchronizing frame acquistion of multiple cameras.

Attributes:
- `pin`: Integer. The Arduino digital pin number to use.
- `pulse_len`: Integer. Time duration in milliseconds between successive pulses. For example, to acquire frames at 20 frames per second this attribute should be 50.
- `pulse_width`: Float. A number between 0 and 1. The pulse duty cycle. The fraction of the pulse period in which the output will be on. For example, a value of 0.8 with a pulse_len of 50ms will result in the digital pin going HIGH for 40ms and then LOW for 10ms before going HIGH again.

Commands:
Like the `line` interface, the `trigger` interface inherits from the toggle interface and has the same commands (`get`, `set`, `toggle`, `periodic`). See the line interface documentation.

Example:
```json
{
    "name": "Camera Trigger",
    "type": "trigger",
    "pin": 12,
    "pulse_len": 17,
    "pulse_width": 0.7,
    "ui": "camera_trigger"
}
```

### `feeder`
Control an EVNICE EV200GW fish feeder (or similar)

Attributes:
- `pins`: Array of 4 integers. The numbers of the pins that are connected to the ULN2003 board.

Commands:
- `dispense`: Dispense one reward from the feeder.

Example:
```json
{
    "name": "Right Feeder",
    "type": "feeder",
    "pins": [5, 6, 7, 8],
    "ui": "action",
    "command": "dispense",
    "icon": "gift"
}
```

### `dallas_temperature`
Communicate with digital temperature sensors such as DS18B20 (one-wire protocol). This uses the DallasTemperature arduino library. Check the [library documentation](https://github.com/milesburton/Arduino-Temperature-Control-Library) for supported devices. This interface can control any number of such sensors connected in parallel over a single Arduino digital pin.

Attributes:
- `pin`: Integer. The one-wire digital pin number. 

Commands:
- `get`: Sends back an array of floats containing the current measurement of each sensor.

Example:
```json
{
    "name": "Temp",
    "type": "dallas_temperature",
    "pin": 2,
    "ui": "sensor",
    "unit": "°",
    "icon": "thermometer-half"
}
```

## Interface UIs
The `ui` attribute determines how the interface is presented in the Arena menu of the ReptiLearn UI. Each `ui` type can have additional interface attributes that configure how it will be displayed in the menu.

### `toggle`

A toggle button that allows setting the interface on or off. It has no additional attributes.

Compatible interfaces: `line`

### `trigger`
This `ui` value tells ReptiLearn to use this interface as a camera trigger. The trigger can be controlled from the trigger button next to the recording button in the UI, or automatically when starting and stopping video recording (in case the trigger was not already running before recording). There are no additional attributes.

Only one interface with the `trigger` ui is supported. Additional interfaces will be ignored by the recording system.

Compatible interfaces: `trigger`

### `action`

A button that sends a command without arguments to the interface. This can be any command.

Attributes:
- `command`: String. The command name. For example, for controlling a `feeder` interface manually it should be set to `dispense`.
- `icon`: String. A name of a FontAwesome icon that will be displayed on the button. See [here](https://fontawesome.com/search?o=r&m=free) for available icons.

Compatible interfaces: any interface that has commands without arguments (e.g. `feeder`)

### `sensor`

Displays the sensor reading, possibly listing multiple sensors that send on the same interface (as in the `dallas_temperature` interface).

Attributes:
- `unit`: String. The units of the sensor value.
- `icon`: String. A name of a FontAwesome icon that will be displayed on the button. See [here](https://fontawesome.com/search?o=r&m=free) for available icons.

Compatible interfaces: `dallas temperature` (but can be used to display the value of any interface).
