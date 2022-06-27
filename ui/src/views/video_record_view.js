import React from 'react';
import { useSelector } from 'react-redux';

import { api_url } from '../config.js';
import { VideoSettingsView } from './video_settings_view.js';
import RLMenu from './ui/menu.js';
import RLButton from './ui/button.js';
import RLIcon from './ui/icon.js';
import RLInput from './ui/input.js';
import { RLTooltip } from './ui/tooltip.js';

export const VideoRecordView = () => {
    const ctrlState = useSelector((state) => state.reptilearn.ctrlState);

    const [openSettingsModal, setOpenSettingsModal] = React.useState(false);
    const [filePrefix, setFilePrefix] = React.useState('');

    if (ctrlState == null)
        return null;

    const image_sources = ctrlState.video?.image_sources ? Object.keys(ctrlState.video.image_sources) : null;
    const is_recording = ctrlState.video?.record?.is_recording;
    const ttl_trigger_state = ctrlState.video?.record?.ttl_trigger;

    const toggle_recording = (e) => {
        if (is_recording) {
            fetch(api_url + "/video_record/stop");
        }
        else {
            fetch(api_url + `/video_record/set_prefix/${filePrefix}`)
                .then(res => fetch(api_url + "/video_record/start"));
        }
    };

    const toggle_ttl_trigger = (e) => {
        if (ctrlState.video.record.ttl_trigger) {
            fetch(api_url + "/video_record/stop_trigger");
        }
        else {
            fetch(api_url + "/video_record/start_trigger");
        }
    };

    const has_trigger = () => {
        if (ctrlState["video"]?.["record"]) {
            return "ttl_trigger" in ctrlState["video"]["record"];
        }
        return false;
    };

    const src_changed = (src_id) => {
        if (ctrlState.video.record.selected_sources.includes(src_id)) {
            fetch(api_url + `/video_record/unselect_source/${src_id}`);
        }
        else {
            fetch(api_url + `/video_record/select_source/${src_id}`);
        }
    };

    const open_settings_modal = () => {
        setOpenSettingsModal(true);
    };

    const video_menu = (() => {
        const src_items = image_sources
            ? image_sources.map(src_id => {
                const selected = ctrlState.video?.record?.selected_sources ? (ctrlState.video.record.selected_sources.indexOf(src_id) !== -1) : false;
                return (
                    <RLMenu.ButtonItem
                        onClick={() => src_changed(src_id)}
                        disabled={!ctrlState.video.image_sources[src_id].acquiring || is_recording}
                        key={src_id}
                    >
                        <RLIcon.MenuIcon icon={selected ? "toggle-on" : "toggle-off"} />
                        <span className='pr-1 align-middle'>{src_id}</span>
                    </RLMenu.ButtonItem>
                );
            })
            : null;


        return (
            <RLMenu button={<RLMenu.TopBarMenuButton title="Video" />}>
                <RLMenu.HeaderItem key="sources">Record sources</RLMenu.HeaderItem>
                {src_items}
                <RLMenu.SeparatorItem key="sep" />
                <RLMenu.ButtonItem onClick={open_settings_modal} disabled={is_recording} key="Video settings">Video settings</RLMenu.ButtonItem>
            </RLMenu>
        );
    })();

    const recording_disabled = !ctrlState.video?.record?.selected_sources || ctrlState.video.record.selected_sources.length === 0;

    return (
        <React.Fragment>
            <VideoSettingsView open={openSettingsModal} setOpen={setOpenSettingsModal} />
            <RLInput.TopBarText
                name="prefix_input"
                placeholder="optional recording id"
                value={filePrefix}
                onChange={(e) => setFilePrefix(e.target.value)}
                disabled={is_recording}
                className='px-2 py-1'
            />
            {ctrlState.video?.record && (
                <RLTooltip content={is_recording ? "Stop recording" : "Start recording"}>
                    <RLButton.TopBarButton
                        onClick={toggle_recording}
                        icon={is_recording ? "stop-circle" : "circle"} iconClassName={is_recording ? "text-green-700" : recording_disabled ? "text-gray-500" : "text-red-500"}
                        disabled={recording_disabled} />
                </RLTooltip>)}

            {has_trigger() && (
                <RLTooltip content={ttl_trigger_state ? "Stop camera trigger" : "Start camera trigger"}>
                    <RLButton.TopBarButton onClick={toggle_ttl_trigger} icon={[(ttl_trigger_state ? "fas" : "far"), "clock"]} />
                </RLTooltip>)}

            {video_menu}
        </React.Fragment>
    );
};
