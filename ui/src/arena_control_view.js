import React from 'react';
import { Dropdown } from 'semantic-ui-react';
import { api_url } from './config.js';

export const ArenaControlView = ({ctrl_state}) => {
    const [arenaConfig, setArenaConfig] = React.useState(null);
    React.useEffect(() => {
        fetch(api_url + "/arena/config")
            .then((res) => res.json())
            .then((arena_config) => setArenaConfig(arena_config));
    }, []);
    
    const toggle_display = (display) => {
	fetch(api_url + `/arena/switch_display/${!ctrl_state.arena.displays[display] ? 1 : 0}`);
    };
    
    const poll_arena = () => {
        fetch(api_url + "/arena/poll");
    };

    const run_command = (command, iface, args, request_values) => {
        let cmd_array = [command, iface];
        if (args && args.length > 0) {
            cmd_array = cmd_array.concat(args);
        }

        fetch(api_url + "/arena/run_command", {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            body: JSON.stringify(cmd_array)
        }).then(() => {
            if (request_values) {
                fetch(api_url + "/arena/request_values/" + iface);
            }
        });
    };
    
    const get_toggle_icon = dev => {
        return ctrl_state.arena.values[dev["name"]] === 1 ? "toggle on" : "toggle off";
    };

    const get_display_toggle_icon = display => {
        return ctrl_state.arena.displays[display] === true ? "toggle on" : "toggle off";
    };
    
    const get_interface_ui = (ifs) => {
        if (ifs.ui === "toggle") {
            return (
                <Dropdown.Item text={ifs.name}
                               icon={get_toggle_icon(ifs)}
                               onClick={() => run_command("toggle", ifs.name, undefined, true)}
                               key={ifs.name}/>
            );                        
        }
        else if (ifs.ui === "action") {
            return (
                <Dropdown.Item text={ifs.name}
                               icon={ifs.icon || null}
                               onClick={() => run_command(ifs["command"], ifs.name, undefined, false)}
                               key={ifs.name}/>
            );
        }
        else if (ifs.ui === "sensor") {
            const make_item = (val, idx) => {
                const format_val = Math.round(val*100) / 100;
                const text = idx !== undefined ?
                      `${ifs.name} ${idx}: ${format_val}${ifs.unit || ''}`
                      : `${ifs.name}: ${format_val}${ifs.unit || ''}`;
                
                return (
                    <Dropdown.Item text={text} icon={ifs.icon || null} key={ifs.name+idx}/>
                );                
            };
            
            if (ctrl_state.arena.values && Object.keys(ctrl_state.arena.values).includes(ifs.name)) {
                const val = ctrl_state.arena.values[ifs.name];
                if (Array.isArray(val)) {
                    return (
                        <React.Fragment key={val}>
                          {val.map(make_item)}
                        </React.Fragment>
                    );                    
                }
                else {
                    return make_item(val);
                }
            }
            else return null;
        }
        else return null;
    };

    const items = !arenaConfig ? null : arenaConfig.map((ifs) => get_interface_ui(ifs));

    const update_time = ((t) => {
        if (t) {
            const timestamp = new Date(0);
            timestamp.setUTCSeconds(t);
            return timestamp;
        }
        else {
            return null;
        }
    })(ctrl_state.arena.timestamp);

    const display_toggles = !ctrl_state.arena.displays ? null : Object.keys(ctrl_state.arena.displays)
          .map((d) => (
              <Dropdown.Item text={d} icon={get_display_toggle_icon(d)} key={d}
                             onClick={() => toggle_display(d)}/>
          ));
   
    return (
        <button>
          <Dropdown text='Arena' scrolling>
            <Dropdown.Menu>
	      {items}
	      <Dropdown.Header>Displays</Dropdown.Header>
              {display_toggles}
              <Dropdown.Divider/>
              {!update_time ? null : (
                  <Dropdown.Item text={`Updated: ${update_time.toLocaleTimeString()}`}
                                 key={update_time}/>
              )}
              <Dropdown.Item text="Poll arena"
                             icon="stethoscope"
                             onClick={poll_arena}/>
            </Dropdown.Menu>
          </Dropdown>
        </button>
    );
};
