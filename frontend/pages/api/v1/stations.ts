import {getStationsMetadata} from '../../../backendServices/stations';
import {NextApiRequest, NextApiResponse} from 'next';
import {StationsMetadata} from '../../../types';

export default function handler(
  req: NextApiRequest,
  res: NextApiResponse<StationsMetadata>,
) {
  return getStationsMetadata().then(stationsMetadata => {
    res.status(200).json(stationsMetadata);
  });
}
