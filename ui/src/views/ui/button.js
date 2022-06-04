import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { classNames, styles } from "./common";
import RLIcon from "./icon";

const RLButton = (props) => (
    <button {...props}>{props.children}</button>
);

const BarButton = ({ text, icon, className, iconClassName, ...props }) => (
    <RLButton {...props} className={classNames(
        "flex items-center border rounded-[4px] border-gray-300 px-1 py-0 bg-white font-medium text-gray-700 hover:bg-gray-200 hover:border-gray-400 origin-top-right h-[22px]",
        styles.disabled,
        styles.focusBorder,
        className)
    }>
        {icon && <FontAwesomeIcon className={classNames("my-auto", iconClassName || "h-[12px] w-[12px]")} icon={icon}/>}
        {text}
    </RLButton>
);

const TopBarButton = ({ text, icon, className, iconClassName, children, ...props }) => (
    <RLButton {...props} className={classNames(
        "flex items-center border border-gray-300 shadow-sm px-2 py-0 bg-white font-medium text-gray-700 hover:bg-gray-200",
        styles.focusBorder,
        styles.disabled,
        className)
    }>
        {children || (
            <div className="flex flex-row items-center gap-1">
                {icon && <FontAwesomeIcon className={classNames("my-auto", iconClassName || "h-[12px] w-[12px]")} icon={icon}/>}
                {text}
            </div>
        )}
    </RLButton>
);

const ModalButton = ({ children, text, icon, className, colorClasses, ...props }) => {
    return (
        <RLButton {...props} type="button" className={classNames(
            "mt-3 w-full inline-flex justify-center rounded-lg border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium hover:bg-gray-50 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm",
            colorClasses || "text-gray-700",
            styles.disabled,
            styles.focusRing,
            className)
        }>
            {children || (
                <div className='flex flex-row items-center gap-1'>
                    {icon && <RLIcon icon={icon}/>}
                    {text}
                </div>

            )}
        </RLButton>
    );
}

RLButton.BarButton = BarButton;
RLButton.TopBarButton = TopBarButton;
RLButton.ModalButton = ModalButton;

export default RLButton