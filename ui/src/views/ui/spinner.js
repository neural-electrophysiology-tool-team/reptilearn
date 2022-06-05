import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

export const RLSpinner = ({ children, ...props }) => (
    <div><FontAwesomeIcon {...props} icon="spinner" className="animate-spin mx-1" />{children}</div>
);