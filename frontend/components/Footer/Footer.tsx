import Link from "next/link";

import styles from "./Footer.module.scss";
import links from "./links.json";

export default function Footer() {
  return (
    <>
      <div className={styles.links}>
        {links.map(link => (
          <Link key={link.name} href={link.href}>
            <a target={link.target}>{link.name}</a>
          </Link>
        ))}
      </div>
    </>
  );
}
