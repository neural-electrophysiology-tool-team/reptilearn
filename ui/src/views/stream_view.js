import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { Resizable } from 'react-resizable';
import 'react-resizable/css/styles.css';

import { api_url } from '../config.js';
import { imageSourceIds, moveStream, removeStream, setStreams, toggleStream, updateStream, updateStreamSources } from '../store/reptilearn_slice.js';
import { Bar } from './ui/bar.js';
import RLButton from './ui/button.js';
import { RLListbox, RLSimpleListbox } from './ui/list_box.js';
import { classNames } from './ui/common.js';

const StreamView = ({ idx }) => {
    const dispatch = useDispatch();

    const streams = useSelector((state) => state.reptilearn.streams);    
    const video_config = useSelector((state) => state.reptilearn.videoConfig);
    const src_ids = useSelector(imageSourceIds);

    const [drag, setDrag] = React.useState(false);
    const [draggedOver, setDraggedOver] = React.useState(false);
    const [dragCount, setDragCount] = React.useState(0); // prevent drag indicator from disappearing on child elements
    const [mouseDownTarget, setMouseDownTarget] = React.useState(null); // drag from handle only
    
    const dragHandle = React.useRef();

    const { src_id, width, undistort, is_streaming } = streams[idx];
    const src_width = video_config.image_sources[src_id].image_shape[1];
    const src_height = video_config.image_sources[src_id].image_shape[0];

    const stream_height = src_height * (width / src_width);
    const stream_url = api_url
        + `/image_sources/${src_id}/stream?width=${width}&fps=5&undistort=${undistort}&ts=${Date.now()}`;

    const on_resize = (e, d) => {
        dispatch(updateStream({idx: idx, key: "width", val: Math.round(d.size.width)}));
    };

    const save_image = () => {
        return fetch(api_url + `/save_image/${src_id}`);
    };

    const handle_drop = (e) => {
        e.preventDefault();
        setDragCount(0);
        setDrag(false);
        setDraggedOver(false);
        const orig_idx = parseInt(e.dataTransfer.getData("text/plain"));
        dispatch(moveStream({from: orig_idx, to: idx}))
    };

    const handle_dragstart = (e) => {
        if (dragHandle.current.contains(mouseDownTarget)) {
            setDrag(true);
            e.dataTransfer.setData("text/plain", idx); 
            e.dataTransfer.effectAllowed = "move";    
        } else {
            e.preventDefault();
        }        
    }

    const handle_dragover = (e) => {
        if (!drag) {
            // allow dragging over a _different_ stream view
            e.preventDefault();
        }
    };

    const handle_dragenter = () => {
        if (dragCount === 0) {
            setDraggedOver(true);
        }
        setDragCount(dragCount + 1);
    };

    const handle_dragleave = () => {
        if (dragCount === 1) {
            setDraggedOver(false);
        }
        setDragCount(dragCount - 1);
    };

    const stream_style = {
        width: (width) + "px",
        height: (stream_height) + "px",
        background: 'black',
    };

    const stream_img = is_streaming ?
        (
            <img src={stream_url}
                width={width}
                height={stream_height}
                alt=""
            />
        ) : null;

    const stream_btn_icon = is_streaming ? "pause" : "play";
    const is_dragged_over = draggedOver && !drag;

    return (
        <Resizable width={width} height={stream_height + 28}
            resizeHandles={['se']}
            lockAspectRatio={true}
            onResize={on_resize}
            minConstraints={[240, 240]}
            maxConstraints={[src_width, src_height]}>

            <div draggable className={classNames("bg-gray-100 inline-block mt-px mr-px border-0", is_dragged_over && "ring-2 ring-green-500")}
                style={{ width: width + 'px', height: stream_height + 28 + 'px' }} 
                onDrop={handle_drop} onDragOver={handle_dragover} onDragEnter={handle_dragenter} onDragLeave={handle_dragleave}
                onDragStart={handle_dragstart} onDragEnd={() => setDrag(false)} onMouseDown={(e) => setMouseDownTarget(e.target)} onMouseUp={() => setMouseDownTarget(null)}>
                <Bar>
                    <RLButton.BarButton onClick={() => dispatch(removeStream({idx}))} icon="xmark"/>
                    <RLSimpleListbox header="Image source" options={RLListbox.simpleOptions(src_ids)} selected={src_id} setSelected={(new_src_id) => dispatch(updateStreamSources({stream_idx: idx, new_src_id, old_src_id: src_id}))} />
                    <RLButton.BarButton onClick={() => dispatch(toggleStream({idx}))} icon={stream_btn_icon} />
                    <RLButton.BarButton onClick={save_image} title="Save image" icon="fa-solid fa-file-image" />
                    <div className={classNames("h-4 w-4 my-auto ml-auto mr-1 cursor-move", draggedOver && "pointer-events-none")} ref={dragHandle}>
                        <FontAwesomeIcon icon="bars" className="h-4 text-gray-600" transform="up-1"/>    
                    </div>                    
                </Bar>
                <div className="stream" style={stream_style}>
                    {stream_img}
                </div>
            </div>
        </Resizable>
    );
};

export const StreamGroupView = () => {
    const ctrl_state = useSelector((state) => state.reptilearn.ctrlState);
    const streams = useSelector((state) => state.reptilearn.streams);
    const dispatch = useDispatch();

    React.useEffect(() => {
        if (localStorage.streams) {
            dispatch(setStreams(JSON.parse(localStorage.streams)));
        }
    }, [dispatch]);

    React.useEffect(() => {
        localStorage.streams = JSON.stringify(streams);
    }, [streams]);
    const stream_views = ctrl_state.video ? streams.map((_, idx) => <StreamView idx={idx} key={idx}/>) : null;

    return (
        <div className="pr-1">
            {stream_views}
        </div>
    );    
};