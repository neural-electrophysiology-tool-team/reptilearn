import React from 'react';
import {Selector} from './components.js';
import {api_url} from './config.js';

const StreamView = ({idx, src_idx, stream_width, undistort, is_streaming, remove_stream, image_sources, sources_config, unused_src_idxs, set_streaming, set_src_idx, set_width, set_undistort, stop_streaming}) => {
    const source_id = image_sources[src_idx];
    const src_width = sources_config[source_id].image_shape[1];
    const src_height = sources_config[source_id].image_shape[0];
    
    const stream_height = src_height * (stream_width / src_width);
    const stream_url = api_url + `/video_stream/${source_id}?width=${stream_width}&fps=5&undistort=${undistort}&ts=${Date.now()}`;

    const toggle_stream = (e) => {
        if (is_streaming)
            stop_streaming(source_id);
        
        set_streaming(idx, !is_streaming);
    };
    
    const stream_div_style = {width: stream_width + "px", height: stream_height + "px"};

    const stream = is_streaming ?
	  (
              <img src={stream_url}
                   width={stream_width}
                   height={stream_height}
                   alt="source stream"
              />
          ) : null;
    
    const stream_btn_title = is_streaming ? "Stop Streaming" : "Start Streaming";

    const width_options = Array(12).fill().map((_, i) => (i+1) * src_width / 12);

    const used_img_srcs = image_sources.filter((id, idx) => {
        return unused_src_idxs.indexOf(idx) === -1 && idx !== src_idx;
    });

    return (
          <div className="stream_view">
            <button onClick={(e) => remove_stream(idx)} disabled={is_streaming}>x</button>
            <Selector options={image_sources}
                      on_select={(_, i) => set_src_idx(idx, i)}
                      selected={src_idx}
                      disabled={is_streaming}
                      disabled_options={used_img_srcs}/>
            <br/>
            <div className="stream" style={stream_div_style}>
              {stream}
            </div>
            <label htmlFor="width_selector">Width: </label>
            <Selector options={width_options}
                      on_select={(w) => set_width(idx, w)}
                      selected={width_options.indexOf(stream_width)}
                      disabled={is_streaming}/>
            <input type="checkbox"
                   name="undistort_checkbox"
                   checked={undistort}
                   onChange={(e) => set_undistort(idx, e.target.checked)}
                   disabled={is_streaming}/>
            <label htmlFor="undistort_checkbox">Undistort </label>                        <button onClick={toggle_stream}>{stream_btn_title}</button>
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
    }

    add_stream = () => {
        const new_stream = {
            src_idx: this.unused_src_idxs()[0],  // there must be at least one, otherwise button is disabled.
            width: 360,
            undistort: false,
            is_streaming: false,
        };
        this.setState({streams: [...this.state.streams, new_stream]});
    }

    set_streaming = (idx, is_streaming) => {
        const streams = this.state.streams;
        streams[idx].is_streaming = is_streaming;
        this.setState({streams: streams});
    }

    set_src_idx = (idx, src_idx) => {
        const streams = this.state.streams;
        streams[idx].src_idx = src_idx;
        this.setState({streams: streams});        
    }

    set_width = (idx, width) => {
        const streams = this.state.streams;
        streams[idx].width = width;
        this.setState({streams: streams});
    }

    set_undistort = (idx, undistort) => {
        const streams = this.state.streams;
        streams[idx].undistort = undistort;
        this.setState({streams: streams});        
    }

    stop_streaming = (src_id) => {
        return fetch(api_url + `/stop_stream/${src_id}`);
    }
    
    render() {
        const stream_views = this.state.streams.map(
            (stream, idx) => <StreamView
                               idx={idx}
                               src_idx={stream.src_idx}
                               stream_width={stream.width}
                               undistort={stream.undistort}
                               is_streaming={stream.is_streaming}
                               remove_stream={this.remove_stream}
                               image_sources={this.image_sources}
                               sources_config={this.sources_config}
                               unused_src_idxs={this.unused_src_idxs()}
                               set_streaming={this.set_streaming}
                               set_src_idx={this.set_src_idx}
                               set_width={this.set_width}
                               set_undistort={this.set_undistort}
                               stop_streaming={this.stop_streaming}
                               key={idx}
                               />

        );
        
        return (
	    <div className="stream_group_view pane-content">
	      <button onClick={this.add_stream}
                      disabled={this.state.streams.length === this.image_sources.length}>Add stream</button>
	      <br/>
              <div className="">
                {stream_views}
              </div>
            </div>
        );     
    }
}
