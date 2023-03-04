import React from 'react';
import { useSelector } from 'react-redux';
import { api } from '../api.js';
import { ArenaSettingsView } from './arena_settings_view.js';

import RLIcon from './ui/icon.js';
import RLMenu from './ui/menu.js';


export const ArenaControlView = () => {
    const ctrl_state = useSelector((state) => state.reptilearn.ctrlState);
    const [showArenaSettingsModal, setShowArenaSettingsModal] = React.useState(false);
    const [isManagingController, setManagingController] = React.useState(null);

    const arena_config = useSelector((state) => state.reptilearn.arenaConfig);

    React.useEffect(() => {
        if (isManagingController !== null) {
            return;
        }

        api.get_config("arena").then((config) => {
            setManagingController(config.run_bridge_process);
        })
    }, [setManagingController, isManagingController]);

    const toggle_display = (display) => {
        // TODO: test with multiple displays
        api.arena.switch_display(!ctrl_state.arena.displays[display] ? 1 : 0, display);
    };

    const run_command = (command, iface, args, request_values) => {
        let cmd_array = [command, iface];
        if (args && args.length > 0) {
            cmd_array = cmd_array.concat(args);
        }
        api.arena.run_command(cmd_array)
            .then(() => {
                if (request_values) {
                    api.arena.request_values(iface);                
                }
            });
    };

    const get_toggle_icon = (dev) => {
        return ctrl_state.arena.values[dev["name"]] === 1 ? "toggle-on" : "toggle-off";
    };

    const get_display_toggle_icon = (display) => {
        return ctrl_state.arena.displays[display] === true ? "toggle-on" : "toggle-off";
    };

    const get_interface_ui = (ifs) => {
        if (ifs.ui === "toggle") {
            return (
                <RLMenu.ButtonItem
                    onClick={() => run_command("toggle", ifs.name, undefined, true)}
                    key={ifs.name}>
                    <RLIcon.MenuIcon icon={["fas", get_toggle_icon(ifs)]} />
                    <span className='pl-1 align-middle'>{ifs.name}</span>
                </RLMenu.ButtonItem>
            );
        }
        else if (ifs.ui === "action") {
            return (
                <RLMenu.ButtonItem
                    onClick={() => run_command(ifs["command"], ifs.name, undefined, false)}
                    key={ifs.name}>
                    <RLIcon.MenuIcon icon={ifs.icon} />
                    <span className="pl-1 align-middle">{ifs.name}</span>
                </RLMenu.ButtonItem>
            );
        }
        else if (ifs.ui === "sensor") {
            const make_item = (val, idx) => {
                const format_val = Math.round(val * 100) / 100;
                const text = idx !== undefined ?
                    `${ifs.name} ${idx}: ${format_val}${ifs.unit || ''}`
                    : `${ifs.name}: ${format_val}${ifs.unit || ''}`;

                return (
                    <RLMenu.StaticItem key={ifs.name + idx}>
                        <RLIcon.MenuIcon icon={ifs.icon}/>
                        <span className="pl-1 align-middle">{text}</span>
                    </RLMenu.StaticItem>
                );
            };

            if (ctrl_state && ctrl_state.arena.values && Object.keys(ctrl_state.arena.values).includes(ifs.name)) {
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

    const interfaces_config = arena_config && Object.values(arena_config).map((port_conf) => port_conf.interfaces).flat()
    const items = !interfaces_config ? null : interfaces_config.map((ifs) => get_interface_ui(ifs));

    const update_time = ((t) => {
        if (t) {
            const timestamp = new Date(0);
            timestamp.setUTCSeconds(t);
            return timestamp;
        }
        else {
            return null;
        }
    })(ctrl_state?.arena.timestamp);

    const display_toggles = ctrl_state?.arena.displays
        ? Object.keys(ctrl_state.arena.displays)
            .map((d) => (
                <RLMenu.ButtonItem
                    key={d}
                    onClick={() => toggle_display(d)}
                >
                    <RLIcon.MenuIcon icon={["fas", get_display_toggle_icon(d)]}/>
                    <span className="pl-1 align-middle">{d}</span>
                </RLMenu.ButtonItem>
            ))
        : null;

    const bridge_button_label = ctrl_state.arena?.bridge?.running ? "Restart arena" : "Start arena";
    const bridge_button_action = () => {
        if (ctrl_state.arena?.bridge?.running) {
            api.arena.restart_bridge();
        } else {
            api.arena.run_bridge();
        }
    }

    return (
        <>
            <ArenaSettingsView setOpen={setShowArenaSettingsModal} open={showArenaSettingsModal} isManagingController={isManagingController} />
            <RLMenu button={<RLMenu.TopBarMenuButton title="Arena" />}>
                {ctrl_state.arena?.bridge?.listening && items}
                {display_toggles.length > 0 && <RLMenu.HeaderItem>Displays</RLMenu.HeaderItem>}
                {display_toggles}
                <RLMenu.SeparatorItem />
                {update_time &&
                    <RLMenu.StaticItem key={update_time}>
                        {`Updated: ${update_time.toLocaleTimeString()}`}
                    </RLMenu.StaticItem>
                }
                <RLMenu.ButtonItem onClick={api.arena.poll} disabled={!ctrl_state.arena?.bridge?.listening}>
                    <RLIcon.MenuIcon icon="stethoscope" />
                    <span>Poll arena</span>
                </RLMenu.ButtonItem>
                <RLMenu.ButtonItem onClick={() => setShowArenaSettingsModal(true)} disabled={false} key="Arena settings">
                    <RLIcon.MenuIcon icon="gear" />
                    <span className="align-middle">Arena settings...</span>
                </RLMenu.ButtonItem>
                <RLMenu.SeparatorItem />
                {isManagingController && <RLMenu.ButtonItem onClick={bridge_button_action} disabled={false} key="bridge_button">
                    <RLIcon.MenuIcon icon={ctrl_state.arena?.bridge?.running ? "undo" : "play"} />
                    <span className="align-middle">{bridge_button_label}</span>
                </RLMenu.ButtonItem>}
                {isManagingController && <RLMenu.ButtonItem onClick={api.arena.stop_bridge} disabled={!ctrl_state.arena?.bridge?.running} key="stop_bridge_button">
                <RLIcon.MenuIcon icon="stop" />
                    <span className="align-middle">Stop arena</span>
                </RLMenu.ButtonItem>}
            </RLMenu>
        </>);
};
