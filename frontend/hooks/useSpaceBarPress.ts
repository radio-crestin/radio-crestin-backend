import {useEffect} from 'react';

const useSpaceBarPress = (callback: any) => {
  useEffect(() => {
    window.addEventListener('keydown', function (e) {
      if (e.keyCode == 32 && e.target == document.body) {
        e.preventDefault();
      }
    });

    const handleKeyPress = (e: any) => {
      if (e.key === ' ' || e.code === 'Space' || e.keyCode === 32) {
        callback();
      }
    };

    document.body.addEventListener('keyup', handleKeyPress);

    return () => {
      document.body.removeEventListener('keyup', handleKeyPress);
    };
  }, [callback]);
};

export default useSpaceBarPress;
