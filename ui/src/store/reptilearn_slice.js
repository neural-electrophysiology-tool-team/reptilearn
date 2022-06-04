import { createSlice } from '@reduxjs/toolkit';
import { api_url } from '../config';

export const reptilearnSlice = createSlice({
    name: 'reptilearn',
    initialState: {
        ctrlState: null,
        videoConfig: null,
        streams: [],
    },
    reducers: {
        setCtrlState: (state, action) => {
            state.ctrlState = action.payload;
        },
        setVideoConfig: (state, action) => {
            state.videoConfig = action.payload;
        },
        setStreams: (state, action) => {            
            state.streams = action.payload;
        },
        addStream: (state, action) => {
            const { src_id } = action.payload;
            const idx = state.streams.length - 1;

            const new_width = state.streams[idx] ? state.streams[idx].width : 360;
            const new_is_streaming = state.streams[idx] ?
                state.streams[idx].is_streaming : true;

            const new_stream = {
                src_id: src_id,
                width: new_width,
                undistort: false,
                is_streaming: new_is_streaming,
            };
            const new_streams = [...state.streams, new_stream];

            state.streams = new_streams;
        },
        updateStreamSources: (state, action) => {
            const { stream_idx, old_src_id, new_src_id } = action.payload;
            const ss = state.streams.map(s => ({ ...s }));
            const ident_ids = ss.map((s, i) => ({ idx: i, src_id: s.src_id }))
                .filter(s => s.src_id === new_src_id && s.idx !== stream_idx);
            if (ident_ids.length > 0) {
                const ident_id = ident_ids[0];
                ss[ident_id.idx].src_id = old_src_id;
            }
            ss[stream_idx].src_id = new_src_id;
            state.streams = ss;
        },
        moveStream: (state, action) => {
            const { from, to } = action.payload;
            const from_stream = state.streams[from];
            state.streams.splice(from, 1);
            state.streams.splice(to, 0, from_stream);
        },
        removeStream: (state, action) => {
            const { idx } = action.payload;
            state.streams = state.streams.slice(0, idx)
                .concat(state.streams.slice(idx + 1, state.streams.length));
        }, 
        updateStream: (state, action) => {
            const { idx, key, val } = action.payload;
            const s = state.streams.map(s => ({ ...s }));
            s[idx][key] = val;
            state.streams = s;
        },
        toggleStream: (state, action) => {
            const { idx } = action.payload;
            const is_streaming = state.streams[idx].is_streaming;
            const src_id = state.streams[idx].src_id;
            
            if (is_streaming) {
                fetch(api_url + `/stop_stream/${src_id}`);
            }                

            state.streams[idx].is_streaming = !is_streaming
        },
    
    },
});

export const imageSourceIds = (state) => {
    return state.reptilearn.videoConfig?.image_sources
        ? Object.keys(state.reptilearn.videoConfig.image_sources)
        : null;
};

export const streamlessSrcIds = (state) => {

    const used_ids = state.reptilearn.streams.map(s => s.src_id);
    return imageSourceIds(state)?.filter(src_id => !used_ids.includes(src_id));
};

export const { setCtrlState, setVideoConfig, setStreams, addStream, updateStreamSources, moveStream, removeStream, updateStream, toggleStream } = reptilearnSlice.actions;

export default reptilearnSlice.reducer;