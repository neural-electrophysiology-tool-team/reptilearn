import React from 'react';
import {Selector} from './components.js';
import {api_url} from './config.js';
import { Icon } from 'semantic-ui-react';

const StreamView = (
    {idx, streams, set_streams, image_sources, sources_config, unused_src_ids, add_stream}
) => {
    const {src_id, width, undistort, is_streaming} = streams[idx];
    const src_width = sources_config[src_id].image_shape[1];
    const src_height = sources_config[src_id].image_shape[0];
    
    const stream_height = src_height * (width / src_width);
    const stream_url = api_url
          + `/video_stream/${src_id}?width=${width}&fps=5&undistort=${undistort}&ts=${Date.now()}`;

    const stop_streaming = (src_id) => {
        return fetch(api_url + `/stop_stream/${src_id}`);
    };

    const update_sources = (new_src_id) => {
        const ss = streams.map(s => ({...s}));
        const ident_ids = ss.map((s, i) => ({idx: i, src_id: s.src_id}))
              .filter(s => s.src_id === new_src_id && s.idx !== idx);
        if (ident_ids.length > 0) {
            const ident_id = ident_ids[0];
            ss[ident_id.idx].src_id = src_id;
        }
        ss[idx].src_id = new_src_id;
        console.log(ss);
        set_streams(ss);
    };

    const remove_stream = () => {
        const new_views = streams.slice(0, idx)
              .concat(streams.slice(idx + 1, streams.length));
        set_streams(new_views);
    };

    
    const update_stream = (key, val) => {
        const s = streams.map(s => ({...s}));
        s[idx][key] = val;
        set_streams(s);
    };
    
    const toggle_stream = () => {
        if (is_streaming)
            stop_streaming(src_id);

        update_stream("is_streaming", !is_streaming);
    };

    const shift_left = () => {
        const ss = streams.map(s => ({...s}));
        const s = ss[idx];
        ss.splice(idx, 1);
        ss.splice(idx - 1, 0, s);
        set_streams(ss);
    };

    const shift_right = () => {
        const ss = streams.map(s => ({...s}));
        const s = ss[idx];
        ss.splice(idx, 1);
        ss.splice(idx + 1, 0, s);
        set_streams(ss);
    };

    const save_image = () => {
        return fetch(api_url + `/save_image/${src_id}`);
    };
    
    const dims_style = {width: (width) + "px", height: (stream_height) + "px"};

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

    const shift_right_disabled = idx === streams.length - 1;
    const shift_left_disabled = idx === 0;

    return (
        <div className="stream_view">
          <div className="toolbar">
            <button onClick={(e) => remove_stream()} disabled={streams.length === 1}>
              <Icon name="x" size="small" fitted />
            </button>
            <Selector options={image_sources}
                      on_select={(src_id, i) => update_sources(src_id) }
                      selected={image_sources.indexOf(src_id)}
                      disabled={false} />
            <button onClick={() => shift_left()} disabled={shift_left_disabled}>
              <Icon name="angle left" fitted/>
            </button>
            <button onClick={() => shift_right()} disabled={shift_right_disabled}>
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
          <div className="stream" style={dims_style}>
            {stream}
          </div>
          <div className="toolbar">
            <label htmlFor="width_selector">Width: </label>
            <Selector options={width_options}
                      on_select={(w) => update_stream("width", w)}
                      selected={width_options.indexOf(width)}
                      disabled={false}/>
            <input type="checkbox"
                   name="undistort_checkbox"
                   checked={undistort}
                   onChange={(e) => update_stream("undistort", e.target.checked)}
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
        if (this.image_sources.length !== 0)
            this.add_stream(0);
    }
    
    unused_src_ids = () => {
        const used_ids = this.state.streams.map(s => s.src_id);
        return this.image_sources.filter(src_id => !used_ids.includes(src_id));
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
                               image_sources={this.image_sources}
                               sources_config={this.sources_config}
                               unused_src_ids={this.unused_src_ids()}
                               add_stream={this.add_stream}
                               key={idx}
                               />

        );
        
        return (
	    <div className="stream_group_view">
              {stream_views}
            </div>
        );     
    }
}
