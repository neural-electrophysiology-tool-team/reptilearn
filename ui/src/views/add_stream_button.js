import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useDispatch, useSelector } from "react-redux";
import { streamlessSrcIds, addStream } from "../store/reptilearn_slice";
import RLButton from "./ui/button";
import { RLTooltip } from "./ui/tooltip";

export const AddStreamButton = () => {
    const dispatch = useDispatch();
    const streamless_src_ids = useSelector(streamlessSrcIds);
    const ctrl_state = useSelector((state) => state.reptilearn.ctrlState);

    return (
        <RLTooltip content="Add video stream">
            <RLButton.TopBarButton disabled={!ctrl_state?.video || streamless_src_ids.length === 0} onClick={() => dispatch(addStream({ src_id: streamless_src_ids[0] }))}>
                <span className="fa-layers fa-fw fa-lg">
                    <FontAwesomeIcon icon="fa-solid fa-video" />
                    <FontAwesomeIcon icon="fa-solid fa-add" transform="shrink-6 left-3" inverse />
                </span>
            </RLButton.TopBarButton>
        </RLTooltip>
    );
};