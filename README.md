# Reptilearn

__ReptiLearn__ is an open-source software system made to simplify building automated behavioral arenas, running closed-loop experiments based on realtime video analysis, and collecting large amounts of time-accurate behavioral data. 

__ReptiLearn__ was created to help us run continuous, long-term, learning experiments tailored to the specific needs and challenges posed by reptile model animals. 

![ReptiLearn user interface](/docs/reptilearn-ui.png)

The __ReptiLearn__ system consists of 3 main parts:
- [system](system): Python software responsible for video acquisition, recording and realtime analysis, as well as controlling custom experiments, and collecting data. Communication with the system can be done over HTTP and Websockets.
- [ui](ui): Web-based user interface for controlling and monitoring the system, written using JavaScript and React.js
- [arena](arena): Software for communication between the system and any number of arduino microcontroller boards. It provides a generic arduino program that can be configured to interface with a large range of electronic devices without writing a single line of Arduino code.

There are several entry points for extending the system to fit your needs by writing Python modules, and calling the ReptiLearn Python API. These include:
- Custom experiments
- Support for new image sources
- Fast realtime analysis of image streams which can include running machine learning models
- General tasks that can be scheduled using the web-UI

See the [programming guide](docs/programming_guide.md) for more details. 

## Getting started

- [Installation](docs/installation.md)
- [User guide](docs/user_guide.md)
- [Programming guide](docs/programming_guide.md)
