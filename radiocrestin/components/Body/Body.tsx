import {ReactChild, ReactFragment, ReactPortal} from "react";

export default function Body(props: { children: boolean | ReactChild | ReactFragment | ReactPortal | null | undefined; }) {

  return <>
    {props.children}
  </>
}
