import React from 'react';
import { useSelector, useDispatch } from 'react-redux';

import { setVideoConfig } from '../store/reptilearn_slice';
import RLModal from './ui/modal.js';
import RLTabs from './ui/tabs.js';
import { RLSimpleListbox } from './ui/list_box.js';
import { RLJSONEditor } from './ui/json_edit.js';
import { RLSpinner } from './ui/spinner.js';
import RLButton from './ui/button.js';
import { Bar } from './ui/bar.js';
import RLInput from './ui/input.js';
import { classNames } from './ui/common.js';
import { api } from '../api';
import deep_equal from 'deep-equal';

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
        return api.video.get_config()
            .then((config) => dispatch(setVideoConfig(config)))
            .catch(err => {
                console.log(`Error while fetching video config: ${err}`);
                setTimeout(fetch_video_config, 5000);
            });
    }, [dispatch]);

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

    if (!video_config) {
        return null;
    }

    const cur_object = activeTabIdx === 0 ? "source" : "observer";
    const cur_class_parent = activeTabIdx === 0 ? "image_sources" : "image_observers";

    const apply = () => {
        setOpen(false);
        api.video.update_config({
            "image_sources": sourcesConfig,
            "image_observers": observersConfig
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
        setImageClasses(null);
        api.video.list_image_classes()
            .then(setImageClasses);

        setAddIdInput('');
        setOpenAddModal(true);
    };

    const add_object = async () => {
        const cfg = (activeTabIdx === 0) ? { ...sourcesConfig } : { ...observersConfig };

        const default_params = await api.video.image_class_params(addClassInput);

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

    const set_selected_observer_source_id = (src_id) => {
        const cfg = { ...observersConfig };        
        cfg[selectedObserver] = {...cfg[selectedObserver], src_id};
        setObserversConfig(cfg);
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

    const dirty = !deep_equal(sourcesConfig, video_config.image_sources) ||
        !deep_equal(observersConfig, video_config.image_observers);

    const video_is_running = !!ctrl_state.video;
    const restart_label = dirty ?
        (video_is_running ? "Apply & restart" : "Apply & start")
        : null;

    const tabPanel = (type) => {
        const selected_obj = type === 'sources' ? selectedSource : selectedObserver
        return {
            title: type === 'sources' ? 'Sources' : 'Observers',
            panel: (
                <div className='flex flex-col overflow-hidden'>
                    <Bar colors="bg-gray-100">
                        {selected_obj && <RLSimpleListbox
                            options={type === 'sources' ? srcs_options : obs_options}
                            selected={selected_obj}
                            setSelected={type === 'sources' ? setSelectedSource : setSelectedObserver} />}
                        <RLButton.BarButton onClick={open_add_modal} icon="add" />
                        <RLButton.BarButton onClick={remove_object} icon="xmark" disabled={!selected_obj} />
                        <RLButton.BarButton onClick={reset_object} icon="undo" disabled={!selected_obj} />                        
                        {selected_obj && type === 'observers' && 
                            <>
                                <span>Image source:</span>
                                <RLSimpleListbox
                                    options={[{key: "none", value: null, label: "Disabled"}, ...srcs_options]}
                                    selected={observersConfig[selectedObserver]["src_id"]}
                                    setSelected={set_selected_observer_source_id} />
                            </>
                        }

                    </Bar>
                    {selected_obj && <RLJSONEditor
                        mainMenuBar={false}
                        navigationBar={false}
                        className="p-1 overflow-y-auto flex-grow"
                        content={{ json: type === 'sources' ? sourcesConfig[selectedSource] : observersConfig[selectedObserver] }}
                        onChange={(updatedContent) => type === 'sources' ? on_source_changed(updatedContent.json, selectedSource) : on_observer_changed(updatedContent.json, selectedObserver)} />
                    }
                </div>
            )
        }
    };
    return (
        <RLModal open={open} setOpen={setOpen} header="Video settings" sizeClasses="w-3/6 h-4/6" contentOverflowClass="overflow-hidden" actions={
            <>
                {restart_label && <RLButton.ModalButton colorClasses="text-green-600" onClick={apply}>{restart_label}</RLButton.ModalButton>}
                <RLButton.ModalButton onClick={() => setOpen(false)}>{dirty ? "Cancel" : "Close"}</RLButton.ModalButton>
            </>
        }>
            {!isLoadingConfig
                ? (
                    <div className="flex flex-grow overflow-hidden">
                        <RLTabs onChange={(index) => setActiveTabIdx(index)} panelClassName="flex-col flex-1 overflow-hidden" tabs={[tabPanel('sources'), tabPanel('observers')]} />
                        <RLModal open={openAddModal} setOpen={setOpenAddModal} sizeClasses="w-2/6 h-1/4" header={<>Add {cur_object}</>}
                            actions={
                                <>
                                    <RLButton.ModalButton onClick={add_object} disabled={add_object_exists() || !addIdInput || addIdInput.trim().length === 0 || !addClassInput}>
                                        Add
                                    </RLButton.ModalButton>
                                    <RLButton.ModalButton onClick={() => setOpenAddModal(false)}>Cancel</RLButton.ModalButton>
                                </>
                            }>
                            <table className="border-separate [border-spacing:0.75rem] w-full">
                                <tbody>
                                    <tr>
                                        <td>Class:</td>
                                        <td>
                                            {imageClasses ? <RLSimpleListbox
                                                className="w-full"
                                                placeholder={`Select ${cur_object} class...`}
                                                setSelected={setAddClassInput}
                                                selected={addClassInput}
                                                options={imageClasses[cur_class_parent].map((c) => ({ label: c.split('.').slice(1).join('.'), key: c, value: c }))} />
                                                : <RLSpinner>Loading...</RLSpinner>
                                            }
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>
                                            Id:
                                        </td>
                                        <td>
                                            <RLInput.Text
                                                placeholder={cur_object + " id"}
                                                value={addIdInput}
                                                onChange={(e) => setAddIdInput(e.target.value)}
                                                className={classNames(add_object_exists() ? 'text-red-500' : '', "w-full")} />
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </RLModal>
                    </div>
                ) : <div>Loading...</div>}
        </RLModal >
    );
};
