import {useEffect} from 'react';

const useSpaceBarPress = (callback: any) => {
  useEffect(() => {
    const handleKeyDown = (e: any) => {
      if (
        e.keyCode === 32 &&
        e.target.getAttribute('contentEditable') !== 'true'
      ) {
        e.preventDefault();
      }
    };

    const handleKeyPress = (e: any) => {
      if (e.key === ' ' || e.code === 'Space' || e.keyCode === 32) {
        callback();
      }
    };

    document.body.addEventListener('keyup', handleKeyPress);
    document.body.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.removeEventListener('keyup', handleKeyPress);
      document.body.removeEventListener('keydown', handleKeyDown);
    };
  }, [callback]);
};

export default useSpaceBarPress;
