import React from 'react';
import {Selector} from './components.js';
import {api_url} from './config.js';

const StreamView = ({idx, streams, remove_stream, image_sources, sources_config, unused_src_idxs, set_streaming, set_src_idx, set_width, set_undistort, stop_streaming, shift_left, shift_right}) => {
    const {src_idx, width, undistort, is_streaming} = streams[idx];
    const source_id = image_sources[src_idx];
    const src_width = sources_config[source_id].image_shape[1];
    const src_height = sources_config[source_id].image_shape[0];
    
    const stream_height = src_height * (width / src_width);
    const stream_url = api_url + `/video_stream/${source_id}?width=${width}&fps=5&undistort=${undistort}&ts=${Date.now()}`;

    const toggle_stream = (e) => {
        if (is_streaming)
            stop_streaming(source_id);
        
        set_streaming(idx, !is_streaming);
    };
    
    const stream_div_style = {width: width + "px", height: stream_height + "px"};

    const stream = is_streaming ?
	  (
              <img src={stream_url}
                   width={width}
                   height={stream_height}
                   alt="source stream"
              />
          ) : null;
    
    const stream_btn_title = is_streaming ? "Stop Streaming" : "Start Streaming";

    const width_options = Array(12).fill().map((_, i) => (i+1) * src_width / 12);

    const used_img_srcs = image_sources.filter((id, idx) => {
        return unused_src_idxs.indexOf(idx) === -1 && idx !== src_idx;
    });

    const shift_right_disabled = idx === streams.length - 1;
    const shift_left_disabled = idx === 0;
    
    return (
        <div className="stream_view">
          <div>
            <button onClick={(e) => remove_stream(idx)} disabled={false}>x</button>
            <Selector options={image_sources}
                      on_select={(_, i) => set_src_idx(idx, i)}
                      selected={src_idx}
                      disabled={false}
                      disabled_options={used_img_srcs}/>
            <button onClick={() => shift_left(idx)} disabled={shift_left_disabled}>&lt;</button>
            <button onClick={() => shift_right(idx)} disabled={shift_right_disabled}>&gt;</button>
          </div>
          <div className="stream" style={stream_div_style}>
            {stream}
          </div>
          <div className="toolbar">
            <label htmlFor="width_selector">Width: </label>
            <Selector options={width_options}
                      on_select={(w) => set_width(idx, w)}
                      selected={width_options.indexOf(width)}
                      disabled={false}/>
            <input type="checkbox"
                   name="undistort_checkbox"
                   checked={undistort}
                   onChange={(e) => set_undistort(idx, e.target.checked)}
                   disabled={false}/>
            <label htmlFor="undistort_checkbox">Undistort </label>                        <button onClick={toggle_stream}>{stream_btn_title}</button>
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
        this.add_stream();
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
        if (this.remove_stream_cb)
            this.remove_stream_cb(new_views.length);
    }

    add_stream = () => {
        const new_stream = {
            src_idx: this.unused_src_idxs()[0],  // there must be at least one, otherwise button is disabled.
            width: 360,
            undistort: false,
            is_streaming: true,
        };
        this.setState({streams: [...this.state.streams, new_stream]});
    }

    copy_streams_state = () => {
        return this.state.streams.map(s => ({...s}));
    }
    
    set_streaming = (idx, is_streaming) => {
        const streams = this.copy_streams_state();
        streams[idx].is_streaming = is_streaming;
        this.setState({streams: streams});
    }

    set_src_idx = (idx, src_idx) => {
        const streams = this.copy_streams_state();
        streams[idx].src_idx = src_idx;
        this.setState({streams: streams});        
    }

    set_width = (idx, width) => {
        const streams = this.copy_streams_state();
        streams[idx].width = width;
        this.setState({streams: streams});
    }

    set_undistort = (idx, undistort) => {
        const streams = this.copy_streams_state();
        streams[idx].undistort = undistort;
        this.setState({streams: streams});        
    }

    stop_streaming = (src_id) => {
        return fetch(api_url + `/stop_stream/${src_id}`);
    }

    on_remove_stream = (cb) => {
        this.remove_stream_cb = cb;
    }

    shift_left = (idx) => {
        const streams = this.copy_streams_state();
        const s = streams[idx];
        streams.splice(idx, 1);
        streams.splice(idx - 1, 0, s);
        this.setState({streams: streams});
    }

    shift_right = (idx) => {
        const streams = this.copy_streams_state();
        const s = streams[idx];
        streams.splice(idx, 1);
        streams.splice(idx + 1, 0, s);
        this.setState({streams: streams});
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
                               remove_stream={this.remove_stream}
                               image_sources={this.image_sources}
                               sources_config={this.sources_config}
                               unused_src_idxs={this.unused_src_idxs()}
                               set_streaming={this.set_streaming}
                               set_src_idx={this.set_src_idx}
                               set_width={this.set_width}
                               set_undistort={this.set_undistort}
                               stop_streaming={this.stop_streaming}
                               shift_left={this.shift_left}
                               shift_right={this.shift_right}
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
