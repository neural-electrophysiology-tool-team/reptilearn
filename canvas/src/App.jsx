/**
 * Author: Tal Eisenberg (2023)
 */

/* eslint-disable react/prop-types */
import React from 'react';
import Konva from 'konva';

import { get_configuration } from './common';
import { MQTT } from './MQTT';
import { setupKonvaMQTTInterface } from './KonvaMqttInterface';
import { ConfigureScreen } from './views/ConfigureScreen';
import { ConnectScreen } from './views/ConnectScreen';

function App() {
  const stageRef = React.useRef();
  const mqttRef = React.useRef();
  const windowSizeRef = React.useRef({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  const [connected, setConnected] = React.useState(false);
  const [connectFailed, setConnectFailed] = React.useState(false);
  const [didUpdateSize, setDidUpdateSize] = React.useState(false);

  const canvas_id = window.location.pathname.slice(1);

  React.useEffect(() => {
    const config = get_configuration();

    if (!config || !canvas_id) {
      return;
    }

    if (stageRef.current && !didUpdateSize) {
      return;
    }

    if (!stageRef.current) {
      stageRef.current = new Konva.Stage({
        container: 'container',
        width: windowSizeRef.current.width,
        height: windowSizeRef.current.height,
        id: 'stage',
      });

      // setup window resize handler
      let resize_timeout;
      addEventListener("resize", () => {
        clearTimeout(resize_timeout)
        resize_timeout = setTimeout(() => {
          if (windowSizeRef.current.width == window.innerWidth && windowSizeRef.current.height == window.innerHeight) {
            return;
          }

          windowSizeRef.current = { width: window.innerWidth, height: window.innerHeight };          
          setDidUpdateSize(true);
        }, 100);
      });
    }

    if (!mqttRef.current) {
      const connect = () => {        
          mqttRef.current = MQTT(canvas_id, config.mqtt_address, () => {
            setConnected(true);
            setConnectFailed(false);
          }, () => {
            setConnected(false);
            setTimeout(connect, 5000);
          }, () => {
            setConnectFailed(true);
            setTimeout(connect, 5000);
          });  
      };
      connect();
    }
    
    const { on_window_resize } = setupKonvaMQTTInterface({
      mqtt: mqttRef.current,
      stage: stageRef.current,
      config, canvas_id,
    })

    if (didUpdateSize) {
      setDidUpdateSize(false);
      stageRef.current.width(windowSizeRef.current.width);
      stageRef.current.height(windowSizeRef.current.height);
      on_window_resize(windowSizeRef.current); 
    }    
  }, [canvas_id, didUpdateSize]);

  return <div>
    <div id="container" className="bg-black" style={{ ...(!connected && { "display": "none" }) }}></div>
    {!canvas_id && <ConfigureScreen />}
    {canvas_id && !connected && <ConnectScreen failed={connectFailed} />}
  </div>
}

export default App;
