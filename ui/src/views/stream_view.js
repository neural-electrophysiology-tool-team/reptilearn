import React from 'react';
import { connect } from 'react-redux';
import { Resizable } from 'react-resizable';
import 'react-resizable/css/styles.css';

import { RLSelect } from './ui/select.js';
import { api_url } from '../config.js';
import { Bar } from './ui/bar.js';
import RLButton from './ui/button.js';
import { RLListbox, RLSimpleListbox } from './ui/list_box.js';

const StreamView = (
    { idx, streams, set_streams, video_config, src_ids, unused_src_ids, add_stream }
) => {
    const { src_id, width, undistort, is_streaming } = streams[idx];
    const src_width = video_config.image_sources[src_id].image_shape[1];
    const src_height = video_config.image_sources[src_id].image_shape[0];

    const stream_height = src_height * (width / src_width);
    const stream_url = api_url
        + `/image_sources/${src_id}/stream?width=${width}&fps=5&undistort=${undistort}&ts=${Date.now()}`;

    const stop_streaming = (src_id) => {
        return fetch(api_url + `/stop_stream/${src_id}`);
    };

    const update_sources = (new_src_id) => {
        const ss = streams.map(s => ({ ...s }));
        const ident_ids = ss.map((s, i) => ({ idx: i, src_id: s.src_id }))
            .filter(s => s.src_id === new_src_id && s.idx !== idx);
        if (ident_ids.length > 0) {
            const ident_id = ident_ids[0];
            ss[ident_id.idx].src_id = src_id;
        }
        ss[idx].src_id = new_src_id;
        set_streams(ss);
    };

    const remove_stream = () => {
        const new_views = streams.slice(0, idx)
            .concat(streams.slice(idx + 1, streams.length));
        set_streams(new_views);
    };

    const update_stream = (key, val) => {
        const s = streams.map(s => ({ ...s }));
        s[idx][key] = val;
        set_streams(s);
    };

    const toggle_stream = () => {
        if (is_streaming)
            stop_streaming(src_id);

        update_stream("is_streaming", !is_streaming);
    };

    const shift_left = () => {
        const ss = streams.map(s => ({ ...s }));
        const s = ss[idx];
        ss.splice(idx, 1);
        ss.splice(idx - 1, 0, s);
        set_streams(ss);
    };

    const shift_right = () => {
        const ss = streams.map(s => ({ ...s }));
        const s = ss[idx];
        ss.splice(idx, 1);
        ss.splice(idx + 1, 0, s);
        set_streams(ss);
    };

    const on_resize = (e, d) => {
        update_stream("width", Math.round(d.size.width));
    };

    const save_image = () => {
        return fetch(api_url + `/save_image/${src_id}`);
    };

    const stream_style = {
        width: (width) + "px",
        height: (stream_height) + "px",
        background: 'black',
    };

    const stream = is_streaming ?
        (
            <img src={stream_url}
                width={width}
                height={stream_height}
                alt=""
            />
        ) : null;

    const stream_btn_icon = is_streaming ? "pause" : "play";

    const shift_right_disabled = idx === streams.length - 1;
    const shift_left_disabled = idx === 0;

    return (
        <Resizable width={width} height={stream_height + 68}
            resizeHandles={['se']}
            lockAspectRatio={true}
            onResize={on_resize}
            className="controls-view"
            minConstraints={[240, 240]}
            maxConstraints={[src_width, src_height]}
        >
            <div className="bg-gray-100 inline-block mt-px mr-px border-0"
                style={{ width: width + 'px', height: stream_height + 68 + 'px' }}>
                <Bar>
                    <RLButton.BarButton onClick={() => remove_stream()} disabled={streams.length === 1} icon="x" iconClassName="h-[11px] w-[11px]" />
                    <RLSimpleListbox options={RLListbox.simpleOptions(src_ids)} selected={src_id} setSelected={(src_id) => update_sources(src_id)} />
                    <RLButton.BarButton onClick={() => shift_left()} disabled={shift_left_disabled} icon="angle-left" />
                    <RLButton.BarButton onClick={() => shift_right()} disabled={shift_right_disabled} icon="angle-right" />
                    <RLButton.BarButton onClick={toggle_stream} icon={stream_btn_icon} />
                    <RLButton.BarButton onClick={save_image} title="Save image" icon="file-image" />
                    <RLButton.BarButton
                        onClick={() => add_stream(idx + 1)}
                        disabled={streams.length === src_ids.length}
                        title="Add stream" icon="add" iconClassName="h-[11px] w-[11px]" />
                </Bar>
                <div className="stream" style={stream_style}>
                    {stream}
                </div>
                <Bar>
                    <label htmlFor="undistort_checkbox">
                        <input type="checkbox" className="mr-1 align-middle"
                            name="undistort_checkbox"
                            checked={undistort}
                            onChange={(e) => update_stream("undistort", e.target.checked)}
                            disabled={false} />
                        <span className="align-middle">Undistort</span>
                    </label>
                </Bar>
            </div>
        </Resizable>
    );
};

class StreamGroupView extends React.Component {
    state = {
        streams: []
    }

    constructor(props) {
        super(props);
        const { video_config } = props;

        if (video_config && video_config.image_sources) {
            this.src_ids = Object.keys(video_config.image_sources);
        }
    }

    componentDidMount() {
        if (this.src_ids && this.src_ids.length !== 0) {
            this.add_stream(0);
        }
    }

    unused_src_ids = () => {
        const used_ids = this.state.streams.map(s => s.src_id);
        return this.src_ids.filter(src_id => !used_ids.includes(src_id));
    }

    add_stream = (idx) => {
        const new_width = this.state.streams[idx] ? this.state.streams[idx].width : 360;
        const new_is_streaming = this.state.streams[idx] ?
            this.state.streams[idx].is_streaming : true;

        const new_stream = {
            src_id: this.unused_src_ids()[0],
            width: new_width,
            undistort: false,
            is_streaming: new_is_streaming,
        };
        const new_streams = [...this.state.streams];
        new_streams.splice(idx + 1, 0, new_stream);

        this.setState({ streams: new_streams });
    }

    render() {
        if (!this.props.ctrl_state?.video || !this.props.video_config) {
            return null;
        }

        const stream_views = this.state.streams.map(
            (stream, idx) => (
                <StreamView
                    idx={idx}
                    streams={this.state.streams}
                    set_streams={s => this.setState({ streams: s })}
                    video_config={this.props.video_config}
                    src_ids={this.src_ids}
                    unused_src_ids={this.unused_src_ids()}
                    add_stream={this.add_stream}
                    key={idx}
                />
            )
        );

        return (
            <div className="pr-1">
                {stream_views}
            </div>
        );
    }
}

export default connect((state) => ({
    ctrl_state: state.reptilearn.ctrlState,
    video_config: state.reptilearn.videoConfig,
}))(StreamGroupView);