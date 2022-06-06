import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { Resizable } from 'react-resizable';
import 'react-resizable/css/styles.css';

import { api_url } from '../config.js';
import { imageSourceIds, moveStream, removeStream, setStreams, startStreaming, stopStreaming, updateStream, updateStreamSources } from '../store/reptilearn_slice.js';
import { Bar } from './ui/bar.js';
import RLButton from './ui/button.js';
import { RLListbox, RLSimpleListbox } from './ui/list_box.js';
import { classNames } from './ui/common.js';

const StreamImage = React.memo(({ src_id, width, height, is_streaming }) => {
    fetch(api_url + `/stop_stream/${src_id}`);

    const stream_url = api_url
        + `/image_sources/${src_id}/stream?width=${width}&ts=${Date.now()}`;

    const stream_style = {
        width: width + "px",
        height: height + "px",
        background: 'black',
    };

    return (
        <div style={stream_style}>
            {is_streaming
                ? (
                    <img src={stream_url}
                        width={width}
                        height={height}
                        alt={"Video stream " + src_id}
                    />
                ) : <FontAwesomeIcon icon="pause" className="text-gray-500 h-full w-full" transform="shrink-10"/>}
        </div>
    );
});

const StreamView = ({ idx }) => {
    const dispatch = useDispatch();

    const streams = useSelector((state) => state.reptilearn.streams);
    const video_config = useSelector((state) => state.reptilearn.videoConfig);
    const src_ids = useSelector(imageSourceIds);

    const [drag, setDrag] = React.useState(false);
    const [draggedOver, setDraggedOver] = React.useState(false);
    const [mouseDownTarget, setMouseDownTarget] = React.useState(null); // drag from handle only
    const [restartStream, setRestartStream] = React.useState(false);
    const [canEscape, setCanEscape] = React.useState(false);

    const dragCount = React.useRef(0); // prevent drag indicator from disappearing on child elements
    const dragHandle = React.useRef();

    const { src_id, width, is_streaming } = streams[idx];
    const src_width = video_config.image_sources[src_id].image_shape[1];
    const src_height = video_config.image_sources[src_id].image_shape[0];

    const stream_btn_icon = is_streaming ? "pause" : "play";
    const is_dragged_over = draggedOver && !drag;
    const bar_height = 28;

    const get_stream_height = (stream) => {
        const { src_id: id, width: w } = stream;
        const src_width = video_config.image_sources[id].image_shape[1];
        const src_height = video_config.image_sources[id].image_shape[0];

        return src_height * (w / src_width);
    }

    const stream_height = get_stream_height(streams[idx])

    const stream_width_from_height = (height) => {
        const { src_id } = streams[idx];
        const src_width = video_config.image_sources[src_id].image_shape[1];
        const src_height = video_config.image_sources[src_id].image_shape[0];

        return src_width * (height / src_height);
    }

    const on_resize = (_, d) => {
        const requestedHeight = d.size.height - bar_height;

        const closestHeight = (idx > 0)
            ? (() => {
                if (idx < streams.length - 1) {
                    const sh_before = get_stream_height(streams[idx - 1]);
                    const sh_after = get_stream_height(streams[idx + 1]);                    
                    return (Math.abs(sh_before - requestedHeight) < Math.abs(sh_after - requestedHeight)) ? sh_before : sh_after;
                } else {
                    return get_stream_height(streams[idx - 1]);
                }
            })()
            : (() => {
                if (idx < streams.length - 1) {
                    return get_stream_height(streams[idx + 1])
                } else {
                    return null;
                }
            })();

        const dh = Math.abs(d.size.height - closestHeight - bar_height);

        let target_width;
        if (!canEscape) {
            if (dh < 10) {
                target_width = stream_width_from_height(closestHeight);
                setTimeout(() => setCanEscape(true), 500);
            } else {
                target_width = d.size.width;
            }
        } else {
            target_width = d.size.width;
            if (dh > 10) {
                setCanEscape(false);
            }
        }

        dispatch(updateStream({ idx: idx, key: "width", val: Math.floor(target_width) }));
    };

    const on_resize_start = () => {
        if (is_streaming) {
            setRestartStream(true);
            dispatch(stopStreaming({ idx }));
        }
    };

    const on_resize_stop = () => {
        if (restartStream) {
            setRestartStream(false);
            dispatch(startStreaming({ idx }));
        }
    };

    const toggle_stream = () => {
        if (is_streaming) {
            dispatch(stopStreaming({ idx }));
        } else {
            dispatch(startStreaming({ idx }));
        }
    };

    const save_image = () => {
        return fetch(api_url + `/save_image/${src_id}`);
    };

    const handle_drop = (e) => {
        e.preventDefault();
        dragCount.current = 0;
        setDrag(false);
        setDraggedOver(false);
        const orig_idx = parseInt(e.dataTransfer.getData("text/plain"));
        dispatch(moveStream({ from: orig_idx, to: idx }))
    };

    const handle_dragstart = (e) => {
        if (dragHandle.current.contains(mouseDownTarget)) {
            setDrag(true);
            e.dataTransfer.setData("text/plain", idx);
            e.dataTransfer.effectAllowed = "move";
        } else {
            e.preventDefault();
        }
    };

    const handle_dragover = (e) => {
        if (!drag) {
            // allow dragging over a _different_ stream view
            e.preventDefault();
        }
    };

    const handle_dragenter = () => {
        if (dragCount.current === 0) {
            setDraggedOver(true);
        }
        dragCount.current += 1;
    };

    const handle_dragleave = () => {
        if (dragCount.current === 1) {
            setDraggedOver(false);
        }
        dragCount.current -= 1;
    };

    return (
        <Resizable width={width} height={stream_height + bar_height}
            resizeHandles={['se']}
            lockAspectRatio={true}
            onResize={on_resize}
            onResizeStart={on_resize_start}
            onResizeStop={on_resize_stop}
            minConstraints={[stream_width_from_height(180), 180]}
            maxConstraints={[src_width, src_height]}>

            <div draggable className={classNames("bg-gray-100 inline-block mt-px mr-px border-0", is_dragged_over && "ring-2 ring-green-500")}
                style={{ width: width + 'px', height: stream_height + 28 + 'px' }}
                onDrop={handle_drop} onDragOver={handle_dragover} onDragEnter={handle_dragenter} onDragLeave={handle_dragleave}
                onDragStart={handle_dragstart} onDragEnd={() => setDrag(false)} onMouseDown={(e) => setMouseDownTarget(e.target)} onMouseUp={() => setMouseDownTarget(null)}>
                <Bar>
                    <RLButton.BarButton onClick={() => dispatch(removeStream({ idx }))} icon="xmark" />
                    <RLSimpleListbox
                        header="Image source"
                        options={RLListbox.valueOnlyOptions(src_ids)}
                        selected={src_id}
                        setSelected={(new_src_id) => dispatch(updateStreamSources({ stream_idx: idx, new_src_id, old_src_id: src_id }))} />
                    <RLButton.BarButton onClick={toggle_stream} icon={stream_btn_icon} />
                    <RLButton.BarButton onClick={save_image} title="Save image" icon="fa-solid fa-file-image" />
                    <div className={classNames("h-4 w-4 my-auto ml-auto cursor-move", draggedOver && "pointer-events-none")} ref={dragHandle}>
                        <FontAwesomeIcon icon="grip-vertical" className="h-4 text-gray-600" transform="up-1" />
                    </div>
                </Bar>
                <StreamImage src_id={src_id} width={width} height={stream_height} is_streaming={is_streaming} />
            </div>
        </Resizable>
    );
};

export const StreamGroupView = () => {
    const ctrl_state = useSelector((state) => state.reptilearn.ctrlState);
    const streams = useSelector((state) => state.reptilearn.streams);
    const dispatch = useDispatch();

    React.useEffect(() => {
        const ls_streams = localStorage.getItem('streams');

        if (ls_streams) {
            dispatch(setStreams(JSON.parse(ls_streams)));
        }
    }, [dispatch]);

    const stream_views = ctrl_state.video ? streams.map((_, idx) => <StreamView idx={idx} key={idx} />) : null;

    return (
        <div className="pr-1 flex flex-row flex-wrap items-start">
            {stream_views}
        </div>
    );
};