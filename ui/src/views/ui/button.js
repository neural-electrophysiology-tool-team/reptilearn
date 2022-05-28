import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { classNames, styles } from "./common";

const RLButton = (props) => (
    <button {...props}>{props.children}</button>
);

const BarButton = ({ text, icon, className, iconClassName, ...props }) => (
    <RLButton {...props} className={classNames(
        "flex items-center border rounded-[4px] border-gray-300 px-2 py-0 bg-white text-sm font-medium text-gray-700 hover:bg-gray-200 hover:border-gray-400 origin-top-right h-6",
        styles.disabled,
        styles.focusBorder,
        className)
    }>
        {icon && <FontAwesomeIcon className={classNames("my-auto", iconClassName || "h-4 w-4")} icon={icon} />}
        {text}
    </RLButton>
);

const TopBarButton = ({ text, icon, className, iconClassName, ...props }) => (
    <RLButton {...props} className={classNames(
        "flex items-center border border-gray-300 shadow-sm px-2 py-0 bg-white text-sm font-medium text-gray-700 hover:bg-gray-200",
        styles.focusBorder,        
        styles.disabled,
        className)
    }>
        {icon && <FontAwesomeIcon className={classNames("my-auto", iconClassName || "h-4 w-4")} icon={icon} />}
        {text}
    </RLButton>
);

const ModalButton = ({ children, className, ...props }) => {
    return (
        <RLButton {...props} type="button" className={classNames(
            "mt-3 w-full inline-flex justify-center rounded-lg border border-gray-300 shadow-sm px-4 py-3 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm",
            styles.disabled,
            styles.focusRing,
            className)
        }>
            {children}
        </RLButton>
    );
}

RLButton.BarButton = BarButton;
RLButton.TopBarButton = TopBarButton;
RLButton.ModalButton = ModalButton;

export default RLButton