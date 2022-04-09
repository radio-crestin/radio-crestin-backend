import styles from "./StationCategories.module.scss";
import stationCategories from "./stationCategories.json";

const handleClick = (id: string) => {
  console.log("Sort items by this id: ", id);
};

interface IStationCategory {
  id: string;
  name: string;
}

export default function StationCategories() {
  return (
    <div className={styles.container}>
      {stationCategories.map((item: IStationCategory) => (
        <div
          className={styles.item_category}
          onClick={() => handleClick(item.id)}>
          {item.name}
        </div>
      ))}
    </div>
  );
}
