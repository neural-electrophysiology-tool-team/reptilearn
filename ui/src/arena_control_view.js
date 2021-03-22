import React from 'react';
import {Dropdown} from 'semantic-ui-react';
import {api_url} from './config.js';

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

    const poll_sensors = () => {
        fetch(api_url + "/arena/sensors_poll/None");
    };
    
    //const get_icon = on => on ? "check circle outline" : "circle outline";
    const get_icon = on => on ? "toggle on" : "toggle off";
    
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
              <Dropdown.Item text="Poll sensors"
                             icon="eye"
                             onClick={poll_sensors}/>
            </Dropdown.Menu>
          </Dropdown>
        </button>
    );
};
