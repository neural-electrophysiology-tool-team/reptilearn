import React from "react";
import RLMenu from "./ui/menu";
import RLModal from "./ui/modal";
import RLButton from "./ui/button";
import { api } from "../api";

export const MainMenu = () => {
    const [openAboutModal, setOpenAboutModal] = React.useState(false);
    const [openConfirmModal, setOpenConfirmModal] = React.useState(false);
    const confirmFunc = React.useRef(null);

    const open_restart_modal = () => {
        confirmFunc.current = api.system.restart;
        setOpenConfirmModal(true);
    };

    const open_shutdown_modal = () => {
        confirmFunc.current = api.system.shutdown;
        setOpenConfirmModal(true);
    };

    return <React.Fragment>
        <RLModal open={openAboutModal} setOpen={setOpenAboutModal} sizeClasses="w-3/6 h-3/6" paddingClasses="p-0 m-0"  contentOverflowClass="overflow-clip">
            <div className="h-full overflow-visible">
                <div className="text-8xl z-10 font-[Roboto] absolute top-32 left-60">
                    <a href="https://github.com/neural-electrophysiology-tool-team/reptilearn" target="_blank" rel="noreferrer">ReptiLearn</a>
                    
                </div>
                <a href="https://github.com/neural-electrophysiology-tool-team/reptilearn" target="_blank" rel="noreferrer">
                    <img src="github-mark.svg" className="text-2xl z-10 font-[Roboto] absolute bottom-4 right-4 h-16 hover:bg-[rgba(93,194,92)] rounded-full" alt="Link to the ReptiLearn github repository" />
                </a>
                
                <img src="reptilearn-logo.png" className="h-[100%] z-0 overflow-visible absolute bottom-0 left-2" alt="ReptiLearn" />
            </div>            
        </RLModal>
        <RLModal open={openConfirmModal} setOpen={setOpenConfirmModal} header="Are you sure?" sizeClasses="w-2/6" actions={
            <React.Fragment>
                <RLButton.ModalButton colorClasses="text-red-500" onClick={confirmFunc.current}>Yes</RLButton.ModalButton>
                <RLButton.ModalButton onClick={() => setOpenConfirmModal(false)}>No</RLButton.ModalButton>
            </React.Fragment>
        }>
            The system will shutdown. If there's an open session it will be stopped and closed.
        </RLModal>

        <RLMenu button={<RLMenu.TopBarMenuButton title="ReptiLearn" />}>
            <RLMenu.ButtonItem onClick={() => setOpenAboutModal(true)} key="about">About</RLMenu.ButtonItem>
            <RLMenu.SeparatorItem key="sep" />
            <RLMenu.ButtonItem onClick={open_restart_modal} key="restart">Restart</RLMenu.ButtonItem>
            <RLMenu.ButtonItem onClick={open_shutdown_modal} key="shutdown">Shutdown</RLMenu.ButtonItem>
        </RLMenu>
    </React.Fragment>;

}