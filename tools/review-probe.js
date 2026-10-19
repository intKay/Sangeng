async (page) => {
  return await page.evaluate(async () => {
    const g = window.__SANGENG__;
    const THREE = await import('/vendor/three/three.module.js');
    const level = g.level, handles = g.interact.handles;
    const enabled = g.player.enabled;
    g.player.enabled = true;
    const stage = new THREE.Group();
    g.level = stage;
    g.interact.handles = [];
    g.camera.updateMatrixWorld(true);
    const forward = g.camera.getWorldDirection(new THREE.Vector3());
    const make = (distance) => {
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(.3,.3,.1), new THREE.MeshBasicMaterial());
      mesh.position.copy(g.camera.position).addScaledVector(forward, distance);
      stage.add(mesh); return mesh;
    };
    const hidden = make(1), target = make(2);
    const a = g.interact.add(hidden, {prompt:'hidden'});
    const b = g.interact.add(target, {prompt:'visible'});
    hidden.visible = false;
    stage.updateMatrixWorld(true);
    g.interact.update(.3);
    const hiddenBlocks = g.interact.current !== b;
    hidden.visible = true;
    g.interact.update(.3);
    a.setPrompt('changed');
    g.interact.update(.3);
    const stalePrompt = g.ui.el.prompt.textContent !== 'changed';
    g.level = level; g.interact.handles = handles;
    g.player.enabled = enabled; g.interact._clear();
    return {hiddenBlocks, stalePrompt};
  });
}

