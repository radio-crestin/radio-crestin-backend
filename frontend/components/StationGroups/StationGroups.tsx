import {StationGroup} from "../../types";
import {Box, Button, Flex} from "@chakra-ui/react";


export default function StationGroups({stationGroups, selectedStationGroupId, selectStationGroupId}: { stationGroups: StationGroup[], selectedStationGroupId: number, selectStationGroupId: any }) {
  return (
    <Flex ml={2} mt={6} mb={9} alignItems='center' gap='2' style={{"overflow": "auto"}} pr={{base: 2, lg: 0}} pb={{base: 3, lg: 0}}>
      {stationGroups.map((stationGroup) => (
        <Box>
          <Button key={stationGroup.id} onClick={() => selectStationGroupId(stationGroup.id)} isActive={stationGroup.id === selectedStationGroupId} >
            {stationGroup.name}
          </Button>
        </Box>
      ))}
    </Flex>
  );
}
