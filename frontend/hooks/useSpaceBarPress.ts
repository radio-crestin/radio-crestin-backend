import {useEffect} from 'react';

const useSpaceBarPress = (callback: () => void) => {
  useEffect(() => {
    const handleKeyDown = (e: any) => {
      const isInputOrTextArea = ['input', 'textarea', 'select'].includes(
        e.target.tagName.toLowerCase(),
      );

      if (
        e.keyCode === 32 &&
        e.target.getAttribute('contentEditable') !== 'true' &&
        !isInputOrTextArea
      ) {
        e.preventDefault();
      }
    };

    const handleKeyPress = (e: any) => {
      const isInputOrTextArea = ['input', 'textarea', 'select'].includes(
        e.target.tagName.toLowerCase(),
      );

      if (
        (e.key === ' ' || e.code === 'Space' || e.keyCode === 32) &&
        !isInputOrTextArea
      ) {
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
