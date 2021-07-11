import React from 'react';
import { Dropdown } from 'semantic-ui-react';
import { api_url } from './config.js';

export const ArenaControlView = ({ctrl_state}) => {
    const dispense_reward = () => {
        fetch(api_url + "/arena/dispense_reward/");
    };

    const toggle_day_lights = () => {
        fetch(api_url + `/arena/day_lights/${!ctrl_state.arena.day_lights}`);
    };

    const toggle_signal_led = () => {
        fetch(api_url + `/arena/signal_led/${!ctrl_state.arena.signal_led}`);
    };

    const toggle_touchscreen = () => {
	fetch(api_url + `/arena/turn_touchscreen/${!ctrl_state.arena.touchscreen}`);
    };
    
    const poll_sensors = () => {
        fetch(api_url + "/arena/sensors_poll/None");
    };

    const get_icon = on => on ? "toggle on" : "toggle off";

    const sensor_items = (() => {
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
                    <Dropdown.Item text={`Update: ${timestamp.toLocaleTimeString()}`}
                                   key={timestamp}/>
                );
            }
            if (items.length > 0)
                items.push(<Dropdown.Divider key="div"/>);
            return items;       
        }
    })();
    
    return (
        <button>
          <Dropdown text='Arena'>
            <Dropdown.Menu>
              <Dropdown.Item text="Reward"
                             onClick={dispense_reward}
                             icon="gift"/>
              <Dropdown.Item text="Signal LED"
                             icon={get_icon(ctrl_state.arena.signal_led)}
                             onClick={toggle_signal_led}/>
              <Dropdown.Item text="Day lights"
                             icon={get_icon(ctrl_state.arena.day_lights)}
                             onClick={toggle_day_lights}/>
	      <Dropdown.Item text="Touchscreen"
                             icon={get_icon(ctrl_state.arena.touchscreen)}
                             onClick={toggle_touchscreen}/>
              <Dropdown.Divider/>
              {sensor_items}
              <Dropdown.Item text="Poll sensors"
                             icon="stethoscope"
                             onClick={poll_sensors}/>
            </Dropdown.Menu>
          </Dropdown>
        </button>
    );
};
