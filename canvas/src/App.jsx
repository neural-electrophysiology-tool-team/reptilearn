import './App.css';
import Konva from 'konva';
import React from 'react';
import Paho from 'paho-mqtt';

const mqtt_address = {
  host: "localhost",
  port: 9001,
}

function App() {
  const stageRef = React.useRef();
  const mqttRef = React.useRef();

  const [connected, setConnected] = React.useState(false);

  React.useEffect(() => {
    if (stageRef.current) {
      return;
    }
  
    const canvas_id = window.location.pathname.slice(1);
    if (!canvas_id) {
      window.location.pathname = "/" + crypto.randomUUID();
    }

    console.log(`Initializing with canvas id '${canvas_id}'`);

    const incoming_topic = `canvas/${canvas_id}/in`;
    const outgoing_topic = `canvas/${canvas_id}/out`;
    
    stageRef.current = new Konva.Stage({
      container: 'container',
      width: window.innerWidth,
      height: window.innerHeight,
      id: 'stage',
    })
    const stage = stageRef.current;

    const tweens = {};
    const images = {};
    const videos = {};

    mqttRef.current = new Paho.Client(mqtt_address.host, mqtt_address.port, canvas_id)
    const mqtt = mqttRef.current;
    
    mqtt.onConnectionLost = (resp) => {
      console.warn('MQTT connection lost', resp);
      setConnected(false)
      mqtt.publish('connection_lost', {});
      // TODO: reconnect
    }

    const publish = (topic, payload) => {
      payload.response_timestamp = Date.now() / 1000;
      const msg = new Paho.Message(JSON.stringify(payload))
      msg.destinationName = outgoing_topic + "/" + topic;
      // console.log("publishing payload", payload, "topic", topic)
      mqtt.publish(msg)
    };

    const publish_error = (payload) => {
      if (payload.error) {
        payload.message += " " + payload.error.toString();
        delete payload.error
      }

      console.error(payload);
      publish("error", payload)
    }

    const get_node = (node_id) => {
      const node = (node_id === "stage") ? stage : stage.findOne('#' + node_id);
      if (!node) {
        throw Error(`Unknown node id '${node_id}'`)
      }
      return node;
    };

    const get_tween = (tween_id) => {
      const tween = tweens[tween_id];
      if (!tween) {
        throw Error(`Unknown tween id '${tween_id}'`);
      }
      return tween;
    };

    const get_image = (image_id) => {
      const image = images[image_id];
      if (!image) {
        throw Error(`Unknown image id '${image_id}'`);
      }
      return image;
    };

    const get_video = (video_id) => {
      const video = videos[video_id];
      if (!video) {
        throw Error(`Unknown video id '${video_id}'`);
      }
      return video;
    }

    const call_method = (obj, method, args) => {
      const m = obj[method];

      if (!m) {
        throw Error(`Unknown method '${method}'`);
      }
      return m.apply(obj, args);
    };

    const set_prop = (obj, prop, value) => {
      const p = obj[prop];

      if (!p) {
        throw Error(`Unknown property '${prop}'`);
      }
      obj[prop] = value;
    }

    const get_prop = (obj, prop) => {
      const p = obj[prop];

      if (p === undefined) {
        throw Error(`Unknown property '${prop}'`);
      }
      return obj[prop];
    }

    const mqtt_requests = {
      reset() {
        for (const id of Object.getOwnPropertyNames(images)) {
          delete images[id];
        }
        for (const id of Object.getOwnPropertyNames(tweens)) {
          delete tweens[id];
        }
        for (const id of Object.getOwnPropertyNames(videos)) {
          delete videos[id];
        }

        stage.destroyChildren();
      },

      on(payload) {
        const { node_id, event_name, handler_id } = payload;
        const node = get_node(node_id);
        if (!node) {
          return;
        }

        node.on(event_name, (e) => {
          publish("on", {
            handler_id, event: e
          })
        })
      },

      off(payload) {
        const { node_id, event_name } = payload;
        const node = get_node(node_id);
        node.off(event_name);
      },

      add(payload) {
        const { container_id, node_class, node_config } = payload;
        if (node_config && node_config.image_id) {
          const image = get_image(node_config.image_id);
          node_config.image = image
          delete node_config.image_id
        }

        if (node_config && node_config.filters) {
          node_config.filters = node_config.filters.map((filter_name) => Konva.Filters[filter_name])
        }

        const container = get_node(container_id);
        container.add(new Konva[node_class](node_config))
      },

      node(payload) {
        // TODO: support filter, easing, image translation (maybe more?) based on method name.
        const { node_id, method, args } = payload;
        const node = get_node(node_id)
        return call_method(node, method, args);
      },

      make_tween(payload) {
        const { tween_id, tween_config } = payload;
        if (!tween_config.node_id) {
          throw Error("node_id key is missing from tween config.")
        }
        const node = get_node(tween_config.node_id);
        tween_config.node = node;
        delete tween_config.node_id;

        if (tween_config.easing) {
          tween_config.easing = Konva.Easings[tween_config.easing];
        }

        tween_config.onUpdate = () => {
          publish("tween_on_update", {tween_id, node: node.toJSON()});
        }
        tween_config.onFinish = () => {
          publish("tween_on_finish", {tween_id, node: node.toJSON()});
        };
        const tween = new Konva.Tween(tween_config);
        tweens[tween_id] = tween;
        return tween;
      },

      remove_tween(payload) {
        const { tween_id } = payload;
        delete tweens[tween_id];
      },

      tween(payload) {
        const { tween_id, method, args } = payload;

        const tween = get_tween(tween_id);
        call_method(tween, method, args);
      },

      load_image(payload) {
        const { image_id, src } = payload;
        const image = new Image();
        images[image_id] = image;
        
        image.onload = (e) => {
          publish("image_onload", {
            image_id, event: e
          });
        };
        image.onerror = (e) => {
          publish("image_onerror", {
            image_id, event: e
          });
        }
        image.src = src;
      },

      remove_image(payload) {
        const { image_id } = payload;
        delete images[image_id];
      },

      load_video(payload) {
        const { video_id, src, muted } = payload;
        const video = document.createElement('video');
        videos[video_id] = { video, anim: null };
        
        video.addEventListener('loadedmetadata', (e) => {
          console.log('video_loadedmetadata', video_id, e);
          publish("video_loadedmetadata", {
            video_id, event: e, video: {
              duration: video.duration,
              width: video.videoWidth,
              height: video.videoHeight,
            }
          });
        });

        video.addEventListener('error', (e) => {
          console.log('video_error', video_id, e);          
          publish("video_error", {
            video_id, event: e
          });
        });
        video.src = src;
        video.muted = muted
      },

      add_video(payload) {
        const { container_id, video_id, node_config } = payload;
        const { video } = get_video(video_id);
        node_config.image = video;   
        const container = get_node(container_id);
        container.add(new Konva.Image(node_config));

        const anim = new Konva.Animation(() => {
          // TODO: publish/collect time updates here
        }, container);
        videos[video_id].anim = anim;
      },

      remove_video(payload) {
        const { video_id } = payload;
        delete videos[video_id];
      },

      video_set_props(payload) {
        const { video_id, props } = payload;
        const { video } = get_video(video_id);
        console.log(video);
        Object.entries(props).forEach(([prop, value]) => set_prop(video, prop, value));        
      },

      video_get_props(payload) {
        const { video_id, props: video_props } = payload;
        const { video } = get_video(video_id);
        const res = video_props.map((prop) => [prop, get_prop(video, prop)])
        return res; 
      },

      play_video(payload) {
        const { video_id } = payload;
        const { video, anim } = get_video(video_id);
        video.play();
        if (anim) {
          anim.start();
        }        
      },

      pause_video(payload) {
        const { video_id } = payload;
        const { video, anim } = get_video(video_id);
        video.pause();
        if (anim) {
          anim.stop();
        }
      },

      echo(payload) {
        return payload;
      },
    }

    mqtt.onMessageArrived = (msg) => {
      // console.log('MQTT message arrived', msg);
      const topic = msg.topic.slice(incoming_topic.length + 1);
      try {
        const request = JSON.parse(msg.payloadString);

        if (!Object.keys(mqtt_requests).includes(topic)) {
          publish_error({ message: `Received unknown command: '${topic}'`, topic, request })
          return;
        }

        try {
          const result = mqtt_requests[topic](request);
          publish("result", { result, topic, request })
        } catch (error) {
          publish_error({ message: `Error running command '${topic}':`, error, topic, request });
        }

      } catch (error) {
        publish_error({ message: "Error parsing payload:", error, payload: msg.payloadString })
      }
    };

    mqtt.connect({
      onSuccess() {
        console.log(`MQTT connected successfully. Subscribing to incoming_topic '${incoming_topic}'`);
        mqtt.subscribe(incoming_topic + '/#');
        publish("connected", { });
        mqtt_requests.reset();
        setConnected(true);        
      }
    });
   
    addEventListener("unload", () => {
      // TODO: not working
      publish("unloading", {});
    })

  }, []);

  return (
    <>
      <div id="container" style={{...(!connected && {"display": "none"})}}></div>
      {!connected && <div>Connecting to {mqtt_address.host}:{mqtt_address.port}...</div>}
    </>
    
  );
}

export default App;
