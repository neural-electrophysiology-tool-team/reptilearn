import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { classNames } from "./common";

const RLIcon = (props) => (
    <FontAwesomeIcon {...props}/> 
);

const MenuIcon = ({className, ...props}) => (
    <RLIcon className={classNames("w-[14px] h-[14px] pr-1 align-middle ", className)} {...props} />
);

RLIcon.MenuIcon = MenuIcon;
export default RLIcon;