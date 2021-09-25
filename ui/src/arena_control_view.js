import React from 'react';
import { Dropdown } from 'semantic-ui-react';
import { api_url } from './config.js';

export const ArenaControlView = ({ctrl_state}) => {
    
    const toggle_touchscreen = () => {
	fetch(api_url + `/arena/turn_touchscreen/${!ctrl_state.arena.touchscreen}`);
    };
    
    const poll_arena = () => {
        fetch(api_url + "/arena/poll");
    };

    const run_command = (command, iface, args, request_values) => {
        let cmd = JSON.stringify([command, iface]);
        if (args) {
            cmd = cmd.concat(args);
        }
        fetch(api_url + "/arena/run_command", {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            body: JSON.stringify([command, iface].concat(args))
        }).then(() => {
            if (request_values) {
                fetch(api_url + "/arena/request_values/" + iface);
            }
        });
    };
    
    const get_toggle_icon = dev => {
        return ctrl_state.arena.values[dev["name"]] == 1 ? "toggle on" : "toggle off";
    };

    const value_items = (() => {
        const st = ctrl_state.arena.sensors;
        if (st == null)
            return null;
        else {
            const items = [];
            if (st.temp != null) {
                st.temp.forEach((temp, i) => items.push(
                    <Dropdown.Item text={`Temp ${i}: ${temp}C`}
                                   icon="thermometer half"
                                   key={i}/>
                ));
            }
            if (st.humidity != null)
                items.push(
                    <Dropdown.Item text={`Humidity: ${st.humidity}%`}
                                   icon="tint"
                                   key="humidity"/>
                );

            if (st.timestamp != null) {
                const timestamp = new Date(0);
                timestamp.setUTCSeconds(st.timestamp);
                items.push(                    
                    <Dropdown.Item text={`Updated: ${timestamp.toLocaleTimeString()}`}
                                   key={timestamp}/>
                );
            }
            if (items.length > 0)
                items.push(<Dropdown.Divider key="div"/>);
            return items;       
        }
    })();

    const get_device_ui = (dev) => {
        if (dev.ui === "toggle") {
            return (
                <Dropdown.Item text={dev.name}
                               icon={get_toggle_icon(dev)}
                               onClick={() => run_command("toggle", dev.name, undefined, true)}/>
            );                        
        }
        else if (dev.ui === "action") {
            return (
                <Dropdown.Item text={dev.name}
                               icon={dev.icon || null}
                               onClick={() => run_command(dev["command"], dev.name, undefined, false)}/>
            );
        }
        else if (dev.ui === "sensor") {
            const make_item = (val, idx) => {
                const format_val = Math.round(val*100) / 100;
                const text = idx !== undefined ?
                      `${dev.name} ${idx}: ${format_val}${dev.unit || ''}`
                      : `${dev.name}: ${format_val}${dev.unit || ''}`;
                
                return (
                    <Dropdown.Item text={text} icon={dev.icon || null}/>   
                );                
            };
            
            if (ctrl_state.arena.values && Object.keys(ctrl_state.arena.values).includes(dev.name)) {
                const val = ctrl_state.arena.values[dev.name];
                if (Array.isArray(val)) {
                    return (
                        <React.Fragment>
                          {val.map(make_item)}
                        </React.Fragment>
                    );                    
                }
                else {
                    return make_item(val);
                }
            }
        }
        else {
            return null;
        }
    };
    
    const items = Object.entries(ctrl_state.arena.config)
          .map(([ifs, devices]) => {
              return (
                  <React.Fragment>
                    <Dropdown.Header>{ifs}</Dropdown.Header>
                    {devices.map(dev => get_device_ui(dev))}
                  </React.Fragment>
              );
          });

    return (
        <button>
          <Dropdown text='Arena' scrolling>
            <Dropdown.Menu>
              {items}
              <Dropdown.Divider/>
              <Dropdown.Item text="Poll arena"
                             icon="stethoscope"
                             onClick={poll_arena}/>
            </Dropdown.Menu>
          </Dropdown>
        </button>
    );
    return null;
};
