import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

const RLIcon = (props) => (
    <FontAwesomeIcon {...props}/> 
);

const MenuIcon = ({className, ...props}) => (
    <RLIcon className={"w-5 h-5 pr-1 align-middle " + (className || '')} {...props} />
);

RLIcon.MenuIcon = MenuIcon;
export default RLIcon;