import React from 'react';
import {Selector} from './components.js';
import {api_url} from './config.js';
import { Icon } from 'semantic-ui-react';

const StreamView = (
    {idx, streams, set_streams, remove_stream, image_sources, sources_config, unused_src_idxs, add_stream}
) => {
    const {src_idx, width, undistort, is_streaming} = streams[idx];
    const source_id = image_sources[src_idx];
    const src_width = sources_config[source_id].image_shape[1];
    const src_height = sources_config[source_id].image_shape[0];
    
    const stream_height = src_height * (width / src_width);
    const stream_url = api_url + `/video_stream/${source_id}?width=${width}&fps=5&undistort=${undistort}&ts=${Date.now()}`;

    const stop_streaming = (src_id) => {
        return fetch(api_url + `/stop_stream/${src_id}`);
    };

    const update_stream = (idx, key, val) => {
        const s = streams.map(s => ({...s}));
        s[idx][key] = val;
        set_streams(s);
    };
    
    const toggle_stream = () => {
        if (is_streaming)
            stop_streaming(source_id);

        update_stream(idx, "is_streaming", !is_streaming);
    };

    const save_image = (src_id) => {
        return fetch(api_url + `/save_image/${source_id}`);
    };
    
    const stream_div_style = {width: (width) + "px", height: (stream_height) + "px"};

    const stream = is_streaming ?
	  (
              <img src={stream_url}
                   width={width}
                   height={stream_height}
                   alt=""
              />
          ) : null;
    
    const stream_btn_icon = is_streaming ? "pause" : "play";

    const width_options = Array(12).fill().map((_, i) => (i+1) * src_width / 12);

    const used_img_srcs = image_sources.filter((id, idx) => {
        return unused_src_idxs.indexOf(idx) === -1 && idx !== src_idx;
    });

    const shift_right_disabled = idx === streams.length - 1;
    const shift_left_disabled = idx === 0;

    const shift_left = (idx) => {
        const ss = streams.map(s => ({...s}));
        const s = ss[idx];
        ss.splice(idx, 1);
        ss.splice(idx - 1, 0, s);
        set_streams(ss);
    };

    const shift_right = (idx) => {
        const ss = streams.map(s => ({...s}));
        const s = ss[idx];
        ss.splice(idx, 1);
        ss.splice(idx + 1, 0, s);
        set_streams(ss);
    };

    return (
        <div className="stream_view">
          <div className="toolbar">
            <button onClick={(e) => remove_stream(idx)} disabled={streams.length === 1}>
              <Icon name="x" size="small" fitted />
            </button>
            <Selector options={image_sources}
                      on_select={(_, i) => update_stream(idx, "src_idx", i)}
                      selected={src_idx}
                      disabled={false}
                      disabled_options={used_img_srcs}/>
            <button onClick={() => shift_left(idx)} disabled={shift_left_disabled}>
              <Icon name="angle left" fitted/>
            </button>
            <button onClick={() => shift_right(idx)} disabled={shift_right_disabled}>
              <Icon name="angle right" fitted/>
            </button>
            <button onClick={toggle_stream}>
              <Icon size="small" fitted name={stream_btn_icon}/>
            </button>
            <button onClick={save_image} title="Save image">
              <Icon  fitted name="file image outline"/>
            </button>
            <button onClick={() => add_stream(idx)}
                    disabled={streams.length === image_sources.length}
                    title="Add stream">
              <Icon size="small" fitted name="add"/>
            </button>
          </div>
          <div className="stream" style={stream_div_style}>
            {stream}
          </div>
          <div className="toolbar">
            <label htmlFor="width_selector">Width: </label>
            <Selector options={width_options}
                      on_select={(w) => update_stream(idx, "width", w)}
                      selected={width_options.indexOf(width)}
                      disabled={false}/>
            <input type="checkbox"
                   name="undistort_checkbox"
                   checked={undistort}
                   onChange={(e) => update_stream(idx, "undistort", e.target.checked)}
                   disabled={false}/>
            <label htmlFor="undistort_checkbox">Undistort </label>
          </div>
        </div>
    );
};

export class StreamGroupView extends React.Component {
    state = {
        streams: []
    }

    constructor(props) {
        super(props);
        const {image_sources, sources_config} = props;
        this.image_sources = image_sources;
        this.sources_config = sources_config;
    }

    componentDidMount() {
        if (this.unused_src_idxs().length !== 0)
            this.add_stream(0);
    }
    
    unused_src_idxs = () => {
        const used_idxs = this.state.streams.map(s => s.src_idx);
        const all_idxs = Array(this.image_sources.length).fill().map((_, i) => i);
        const unused_idxs = all_idxs.filter(i => used_idxs.indexOf(i) === -1);
        return unused_idxs;
    }
    
    remove_stream = (idx) => {
        const new_views = this.state.streams.slice(0, idx)
              .concat(this.state.streams.slice(idx + 1, this.state.streams.length));
        this.setState({streams: new_views});
    }

    add_stream = (idx) => {
        const new_width = this.state.streams[idx] ? this.state.streams[idx].width : 360;
        const new_is_streaming = this.state.streams[idx] ?
              this.state.streams[idx].is_streaming : true;
        
        const new_stream = {
            src_idx: this.unused_src_idxs()[0],
            width: new_width,
            undistort: false,
            is_streaming: new_is_streaming,
        };
        const new_streams = [...this.state.streams];
        new_streams.splice(idx + 1, 0, new_stream);        
        
        this.setState({streams: new_streams});
    }
        
    shouldComponentUpdate(next_props, next_state) {
        if (JSON.stringify(next_state) !== JSON.stringify(this.state))
            return true;
            
        const next_srcs = next_props.image_sources;
        const prev_srcs = this.props.image_sources;
        if (next_srcs.length !== prev_srcs.length)
            return true;
        
        for (let i=0; i<next_srcs.length; i++)
            if (next_srcs[i] !== prev_srcs[i])
                return true;

        return false;
    }
    
    render() {
        const stream_views = this.state.streams.map(
            (stream, idx) => <StreamView
                               idx={idx}
                               streams={this.state.streams}
                               set_streams={s => this.setState({streams: s})}
                               remove_stream={this.remove_stream}
                               image_sources={this.image_sources}
                               sources_config={this.sources_config}
                               unused_src_idxs={this.unused_src_idxs()}
                               add_stream={this.add_stream}
                               key={idx}
                               />

        );
        
        return (
	    <div className="stream_group_view pane-content">
              {stream_views}
            </div>
        );     
    }
}
