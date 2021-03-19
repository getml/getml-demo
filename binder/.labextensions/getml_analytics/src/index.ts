import {
  JupyterFrontEnd, JupyterFrontEndPlugin
} from '@jupyterlab/application';


/**
 * Initialization data for the getml_analytics extension.
 */
const extension: JupyterFrontEndPlugin<void> = {
  id: 'getml_analytics',
  autoStart: true,
  activate: (app: JupyterFrontEnd) => {
    console.log('JupyterLab extension getml_analytics is enabled')
    let node = document.createElement('script'); //
    node.src = 'https://getml.com/assets/js/tags.js';
    node.type = 'text/javascript';
    node.async = true;
  
    document.getElementsByTagName('head')[0].appendChild(node);
  }
};

export default extension;
