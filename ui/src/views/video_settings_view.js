import React from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

import { api_url } from '../config.js';
import { setVideoConfig } from '../store/reptilearn_slice';
import RLModal from './ui/modal.js';
import RLTabs from './ui/tabs.js';
import { RLSimpleListbox } from './ui/list_box.js';
import { RLJsonEdit } from './ui/json_edit.js';
import RLButton from './ui/button.js';
import { Bar } from './ui/bar.js';

export const VideoSettingsView = ({ setOpen, open }) => {
    const dispatch = useDispatch();
    const [openAddModal, setOpenAddModal] = React.useState(false);
    const [addIdInput, setAddIdInput] = React.useState(null);
    const [addClassInput, setAddClassInput] = React.useState(null);
    const [activeTabIdx, setActiveTabIdx] = React.useState(0);
    const [sourcesConfig, setSourcesConfig] = React.useState({});
    const [observersConfig, setObserversConfig] = React.useState({});
    const [imageClasses, setImageClasses] = React.useState(null);
    const [selectedSource, setSelectedSource] = React.useState(null);
    const [selectedObserver, setSelectedObserver] = React.useState(null);
    const [isLoadingConfig, setLoadingConfig] = React.useState(true);

    const video_config = useSelector((state) => state.reptilearn.videoConfig);
    const ctrl_state = useSelector((state) => state.reptilearn.ctrlState);


    // TODO: this is copied from App.js. should be somewhere else...
    const fetch_video_config = React.useCallback(() => {
        return fetch(api_url + '/video/get_config')
            .then((res) => res.json())
            .then((config) => dispatch(setVideoConfig(config)))
            .catch(err => {
                console.log(`Error while fetching video config: ${err}`);
                setTimeout(fetch_video_config, 5000);
            });
    }, [dispatch]);

    React.useEffect(() => {
        fetch(api_url + '/video/list_image_classes')
            .then((res) => res.json())
            .then(setImageClasses);
    }, [setImageClasses]);

    React.useEffect(() => {
        if (!open) {
            return;
        }

        fetch_video_config().then(() => {
            setLoadingConfig(false);
            const srcs_conf = video_config.image_sources;
            const obs_conf = video_config.image_observers;

            setSourcesConfig(srcs_conf);
            setObserversConfig(obs_conf);

            if (Object.keys(srcs_conf).length > 0) {
                setSelectedSource(Object.keys(srcs_conf)[0]);
            }
            if (Object.keys(obs_conf).length > 0) {
                setSelectedObserver(Object.keys(obs_conf)[0]);
            }
        });

    }, [open]);

    if (!video_config || !imageClasses) {
        return null;
    }

    const cur_object = activeTabIdx === 0 ? "source" : "observer";
    const cur_class_parent = activeTabIdx === 0 ? "image_sources" : "image_observers";

    const shutdown = () => {
        setOpen(false)

        fetch(api_url + '/video/shutdown')
            .catch((e) => {
                console.log('Error while shutting down video system:', e);
            })

    }
    const apply = () => {
        setOpen(false);

        fetch(api_url + '/video/update_config', {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                "image_sources": sourcesConfig,
                "image_observers": observersConfig
            })
        })
            .then((resp) => {
                if (fetch_video_config) {
                    return fetch_video_config();
                }
                else {
                    return resp;
                }
            })
            .catch((e) => {
                console.log("Error while updating config:", e);
            });
    };

    const open_add_modal = () => {
        // const classes = imageClasses[cur_class_parent];
        // if (classes && classes.length > 0) {
        //     setAddClassInput(imageClasses[cur_class_parent][0]);
        // }

        setAddIdInput('');
        setOpenAddModal(true);
    };

    const add_object = async () => {
        const cfg = (activeTabIdx === 0) ? { ...sourcesConfig } : { ...observersConfig };

        const default_params = await fetch(`${api_url}/video/image_class_params/${addClassInput}`).then((resp) => resp.json())

        cfg[addIdInput] = {
            ...default_params,
            class: addClassInput
        };

        if (activeTabIdx === 0) {
            setSourcesConfig(cfg);
            setSelectedSource(addIdInput);
        }
        else if (activeTabIdx === 1) {
            setObserversConfig(cfg);
            setSelectedObserver(addIdInput);
        }

        setOpenAddModal(false);
    };

    const remove_object = () => {
        const cfg = (activeTabIdx === 0) ? { ...sourcesConfig } : { ...observersConfig };

        delete cfg[(activeTabIdx === 0) ? selectedSource : selectedObserver];

        if (activeTabIdx === 0) {
            setSourcesConfig(cfg);
            setSelectedSource(Object.keys(cfg)[0]);
        }
        else if (activeTabIdx === 1) {
            setObserversConfig(cfg);
            setSelectedObserver(Object.keys(cfg)[0]);
        }
    };

    const reset_object = () => {
        const cfg = (activeTabIdx === 0) ? { ...sourcesConfig } : { ...observersConfig };

        const obj_id = (activeTabIdx === 0) ? selectedSource : selectedObserver;

        if (activeTabIdx === 0) {
            cfg[obj_id] = video_config.image_sources[obj_id];
            setSourcesConfig(cfg);
        }
        else if (activeTabIdx === 1) {
            cfg[obj_id] = video_config.image_observers[obj_id];
            setObserversConfig(cfg);
        }
    };

    const add_object_exists = () => {
        if (activeTabIdx === 0) {
            return Object.keys(sourcesConfig).includes(addIdInput);
        }
        else {
            return Object.keys(observersConfig).includes(addIdInput);
        }
    };

    const on_source_changed = (config, src_id) => {
        const c = { ...sourcesConfig };
        c[src_id] = config;
        setSourcesConfig(c);
    };

    const on_observer_changed = (config, src_id) => {
        const c = { ...observersConfig };
        c[src_id] = config;
        setObserversConfig(c);
    };
    const srcs_options = Object.keys(sourcesConfig).map(src_id => ({
        key: src_id,
        label: src_id,
        value: src_id
    }));

    const obs_options = Object.keys(observersConfig).map(obs_id => ({
        key: obs_id,
        label: obs_id,
        value: obs_id
    }));

    const is_obj = (obj) => obj != null && typeof (obj) === 'object';

    const deep_equals = (o1, o2) => {
        const ks1 = Object.keys(o1);
        const ks2 = Object.keys(o2);

        if (ks1.length !== ks2.length) {
            return false;
        }

        for (const k of ks1) {
            const v1 = o1[k];
            const v2 = o2[k];
            const are_objs = is_obj(v1) && is_obj(v2);
            if ((are_objs && !deep_equals(v1, v2)) || (!are_objs && v1 !== v2))
                return false;
        }

        return true;
    };

    const dirty = !deep_equals(sourcesConfig, video_config.image_sources) ||
        !deep_equals(observersConfig, video_config.image_observers);

    const video_is_running = !!ctrl_state.video;
    const restart_label = dirty ?
        (video_is_running ? "Apply & restart" : "Apply & start")
        : (video_is_running ? "Restart" : "Start");

    const tabPanel = (type) => ({
        title: type === 'sources' ? 'Sources' : 'Observers',
        panel: (
            <div className='flex flex-col h-full'>
                <Bar>
                    <RLSimpleListbox
                        options={type === 'sources' ? srcs_options : obs_options}
                        selected={type === 'sources' ? selectedSource : selectedObserver}
                        setSelected={type === 'sources' ? setSelectedSource : setSelectedObserver} />
                    <RLButton.BarButton onClick={open_add_modal} icon="add" />
                    <RLButton.BarButton onClick={remove_object} icon="x" />
                    <RLButton.BarButton onClick={reset_object} icon="undo" />
                </Bar>
                <div className="overflow-y-auto flex-1">
                    <RLJsonEdit
                        src={type === 'sources' ? sourcesConfig[selectedSource] : observersConfig[selectedObserver]}
                        name={null}
                        onEdit={(e) => (type === 'sources' ? on_source_changed(e.updated_src, selectedSource) : on_observer_changed(e.updated_src, selectedObserver))}
                        onAdd={(e) => (type === 'sources' ? on_source_changed(e.updated_src, selectedSource) : on_observer_changed(e.updated_src, selectedObserver))}
                        onDelete={(e) => (type === 'sources' ? on_source_changed(e.updated_src, selectedSource) : on_observer_changed(e.updated_src, selectedObserver))} />
                </div>
            </div>
        )
    });
    return (
        <RLModal open={open} setOpen={setOpen} header="Video settings" sizeClasses="w-4/6 h-4/6" contentOverflowClass="overflow-hidden" actions={
            <React.Fragment>
                {video_is_running ? <RLButton.ModalButton className="text-red-500" onClick={shutdown}>Shutdown</RLButton.ModalButton> : null}
                <RLButton.ModalButton className="text-red-500" onClick={apply}>{restart_label}</RLButton.ModalButton>
                <RLButton.ModalButton onClick={() => setOpen(false)}>{dirty ? "Cancel" : "Close"}</RLButton.ModalButton>
            </React.Fragment>
        }>
            {!isLoadingConfig
                ? (
                    <>
                        <RLTabs onChange={(index) => setActiveTabIdx(index)} tabs={[tabPanel('sources'), tabPanel('observers')]} />
                        <RLModal open={openAddModal} setOpen={setOpenAddModal} className="w-3/6" actions={
                            <>
                                <RLButton.ModalButton onClick={() => setOpenAddModal(false)}>Cancel</RLButton.ModalButton>
                                <RLButton.ModalButton onClick={add_object} disabled={add_object_exists() || !addIdInput || addIdInput.trim().length === 0}>
                                    Add
                                </RLButton.ModalButton>
                            </>
                        }>
                            <h1>Add {cur_object}</h1>
                            <table>
                                <tbody>
                                    <tr>
                                        <td>Class</td>
                                        <td>
                                            <RLSimpleListbox
                                                placeholder={`Select ${cur_object} class...`}
                                                setSelected={setAddClassInput}
                                                selected={addClassInput}
                                                options={imageClasses[cur_class_parent].map((c) => ({ label: c.split('.').slice(1).join('.'), key: c, value: c }))} />
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>
                                            Id:
                                        </td>
                                        <td>
                                            <input placeholder={cur_object + " id"}
                                                value={addIdInput}
                                                onChange={(e) => setAddIdInput(e.target.value)}
                                                className={add_object_exists() ? 'text-red-500' : ''} />
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </RLModal>
                    </>
                ) : <div>Loading...</div>}
        </RLModal >
    );
};
