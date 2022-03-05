import React from 'react';
import { api_url } from './config.js';
import { Input, Grid, Divider, Dropdown, Modal, Button, Icon, Tab } from 'semantic-ui-react';
import ReactJson from 'react-json-view';

export const VideoSettingsView = ({ video_config, fetch_video_config, setOpen, open, ctrl_state }) => {
    const [openAddModal, setOpenAddModal] = React.useState(false);
    const [addIdInput, setAddIdInput] = React.useState(null);
    const [addClassInput, setAddClassInput] = React.useState(null);
    const [activeTabIdx, setActiveTabIdx] = React.useState(0);
    const [sourcesConfig, setSourcesConfig] = React.useState({});
    const [observersConfig, setObserversConfig] = React.useState({});
    const [imageClasses, setImageClasses] = React.useState(null);
    const [selectedSource, setSelectedSource] = React.useState(null);
    const [selectedObserver, setSelectedObserver] = React.useState(null);

    React.useEffect(() => {
        fetch(api_url + '/video/list_image_classes')
            .then((res) => res.json())
            .then(setImageClasses);
    }, [setImageClasses]);

    React.useEffect(() => {
        if (!open) {
            return;
        }

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
    }, [open, video_config]);

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
        const classes = imageClasses[cur_class_parent];
        if (classes && classes.length > 0) {
            setAddClassInput(imageClasses[cur_class_parent][0]);
        }

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

    const on_selected_src_changed = (e, { value }) => setSelectedSource(value);
    const on_selected_obs_changed = (e, { value }) => setSelectedObserver(value);

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
        text: src_id,
        value: src_id
    }));

    const obs_options = Object.keys(observersConfig).map(obs_id => ({
        key: obs_id,
        text: obs_id,
        value: obs_id
    }));

    const panes = [
        {
            menuItem: 'Sources', render: () => (
                <Tab.Pane>
                    <Dropdown placeholder='Select image source'
                        selection
                        options={srcs_options}
                        value={selectedSource}
                        onChange={on_selected_src_changed} />
                    <Button icon size="tiny" onClick={open_add_modal}><Icon name="add" /></Button>
                    <Button icon size="tiny" onClick={remove_object}><Icon name="delete" /></Button>
                    <Button icon size="tiny" onClick={reset_object}><Icon name="undo" /></Button>
                    <Divider />
                    <ReactJson src={sourcesConfig[selectedSource]}
                        name={null}
                        onEdit={(e) => on_source_changed(e.updated_src, selectedSource)}
                        onAdd={(e) => on_source_changed(e.updated_src, selectedSource)}
                        onDelete={(e) => on_source_changed(e.updated_src, selectedSource)} />
                </Tab.Pane>
            )
        },
        {
            menuItem: 'Observers', render: () => (
                <Tab.Pane>
                    <Dropdown placeholder='Select image observer'
                        selection
                        options={obs_options}
                        value={selectedObserver}
                        onChange={on_selected_obs_changed} />
                    <Button icon size="tiny" onClick={open_add_modal}><Icon name="add" /></Button>
                    <Button icon size="tiny" onClick={remove_object}><Icon name="delete" /></Button>
                    <Button icon size="tiny" onClick={reset_object}><Icon name="undo" /></Button>
                    <Divider />
                    <ReactJson src={observersConfig[selectedObserver]}
                        name={null}
                        onEdit={(e) => on_observer_changed(e.updated_src, selectedObserver)}
                        onAdd={(e) => on_observer_changed(e.updated_src, selectedObserver)}
                        onDelete={(e) => on_observer_changed(e.updated_src, selectedObserver)} />
                </Tab.Pane>
            )
        }
    ];

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

    return (
        <React.Fragment>
            <Modal onClose={() => setOpenAddModal(false)}
                open={openAddModal}
                size='tiny'>
                <Modal.Header>Add {cur_object}</Modal.Header>
                <Modal.Content>
                    <Grid columns={2} verticalAlign='middle'>
                        <Grid.Row>
                            <Grid.Column width={4}>Class</Grid.Column>
                            <Grid.Column width={12}>
                                <Dropdown selection
                                    fluid
                                    onChange={(e, opt) => setAddClassInput(opt.value)}
                                    value={addClassInput}
                                    options={imageClasses[cur_class_parent].map((c) => ({ text: c.split('.').slice(1).join('.'), key: c, value: c }))} />
                            </Grid.Column>
                        </Grid.Row>
                        <Grid.Row>
                            <Grid.Column width={4}>Id:</Grid.Column>
                            <Grid.Column width={12}>
                                <Input placeholder={cur_object + " id"}
                                    value={addIdInput}
                                    onChange={(e, { value }) => setAddIdInput(value)}
                                    fluid
                                    error={add_object_exists()} />
                            </Grid.Column>
                        </Grid.Row>
                    </Grid>
                </Modal.Content>
                <Modal.Actions>
                    <Button onClick={() => setOpenAddModal(false)}>Cancel</Button>
                    <Button positive onClick={add_object}
                        disabled={add_object_exists() || !addIdInput || addIdInput.trim().length === 0}>Add</Button>
                </Modal.Actions>
            </Modal>
            <Modal
                onClose={() => setOpen(false)}
                open={open}
                size='small'>
                <Modal.Header>Video settings</Modal.Header>
                <Modal.Content scrolling>
                    <Tab panes={panes} activeIndex={activeTabIdx}
                        onTabChange={(e, { activeIndex }) => setActiveTabIdx(activeIndex)} />
                </Modal.Content>
                <Modal.Actions>
                    {video_is_running ? <Button negative onClick={shutdown}>{"Shutdown"}</Button> : null}
                    <Button positive onClick={apply}>{restart_label}</Button>
                    <Button onClick={() => setOpen(false)}>{dirty ? "Cancel" : "Close"}</Button>
                </Modal.Actions>
            </Modal>
        </React.Fragment>
    );

};
