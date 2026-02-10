import React, { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Card } from './ui/card';
import { Button } from './ui/button';
import ReactFlow, { MiniMap, Controls, Background, addEdge, useNodesState, useEdgesState, Connection, Edge } from 'reactflow';
import 'reactflow/dist/style.css';
import { saveAs } from 'file-saver';
import { VisualProgrammingPalette } from './VisualProgrammingPalette';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from './ui/dialog';
import { Select, SelectItem, SelectTrigger, SelectContent } from './ui/select';
import { EditableNodeWrapper } from './EditableNodeWrapper';
import { DefaultEdge } from './DefaultEdge';
import { nodeTypes, edgeTypes } from './reactflowTypes';

/**
 * VisualProgrammingInterface
 * No-code/Low-code visual programming interface for non-devs.
 * - Flowchart → Code
 * - Architecture diagrams → Implementation
 * - Mockup → Frontend code
 * - Reverse: Code → Visual representation
 */
export const VisualProgrammingInterface: React.FC = () => {
  const { t } = useTranslation('visualProgramming');
  const [nodes, setNodes, onNodesChange] = useNodesState([
    { id: '1', position: { x: 250, y: 5 }, data: { label: t('newFlowchart') }, type: 'editable' }
  ]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [diagramType, setDiagramType] = useState<'flowchart' | 'architecture' | 'mockup'>('flowchart');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const loadInputRef = useRef<HTMLInputElement>(null);
  const [showFrameworkModal, setShowFrameworkModal] = useState(false);
  const [pendingNode, setPendingNode] = useState<{ id: string; type: string; position: { x: number; y: number } } | null>(null);
  const [selectedFramework, setSelectedFramework] = useState<string>('');

  // Frameworks par type
  const FRAMEWORKS: Record<string, { value: string; labelKey: string }[]> = {
    frontend: [
      { value: 'react', labelKey: 'react' },
      { value: 'angular', labelKey: 'angular' },
      { value: 'vue', labelKey: 'vue' },
      { value: 'svelte', labelKey: 'svelte' },
    ],
    backend: [
      { value: 'node', labelKey: 'node' },
      { value: 'django', labelKey: 'django' },
      { value: 'spring', labelKey: 'spring' },
      { value: 'flask', labelKey: 'flask' },
    ],
    database: [
      { value: 'postgres', labelKey: 'postgres' },
      { value: 'mysql', labelKey: 'mysql' },
      { value: 'mongodb', labelKey: 'mongodb' },
      { value: 'sqlite', labelKey: 'sqlite' },
    ],
    api: [
      { value: 'rest', labelKey: 'rest' },
      { value: 'graphql', labelKey: 'graphql' },
      { value: 'grpc', labelKey: 'grpc' },
    ],
  };

  const onConnect = (params: Edge | Connection) => setEdges((eds) => addEdge(params, eds));

  // Ajout d'un nouveau bloc/module
  const handleAddNode = () => {
    const newId = (nodes.length + 1).toString();
    setNodes((nds) => [
      ...nds,
      {
        id: newId,
        position: { x: 100 + 50 * nodes.length, y: 100 + 30 * nodes.length },
        data: { label: t('newBlock', 'Nouveau bloc'), onRename: handleRenameNode },
        type: 'editable',
      },
    ]);
  };

  const handleExportCode = () => {
    // Simple code generation example (flowchart to pseudo-code)
    let code = '';
    if (diagramType === 'flowchart') {
      code = nodes.map((n) => `// Node: ${n.data.label}`).join('\n');
      code += '\n// Edges:';
      code += edges.map((e) => `\n// ${e.source} -> ${e.target}`).join('');
    } else if (diagramType === 'architecture') {
      code = '// Architecture diagram export not implemented yet.';
    } else if (diagramType === 'mockup') {
      code = '// Mockup export not implemented yet.';
    }
    saveAs(new Blob([code], { type: 'text/plain' }), `${diagramType}-export.txt`);
  };

  const handleImportCode = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      // TODO: parse code and generate nodes/edges
      // Pour l'instant, on affiche juste le contenu dans un node
      setNodes([
        { id: 'imported', position: { x: 100, y: 100 }, data: { label: e.target?.result as string }, type: 'default' }
      ]);
      setEdges([]);
    };
    reader.readAsText(file);
  };

  // Persistance locale (sauvegarde/chargement)
  const handleSave = () => {
    const data = JSON.stringify({ nodes, edges, diagramType });
    saveAs(new Blob([data], { type: 'application/json' }), `${diagramType}-diagram.json`);
  };
  const handleLoad = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        setNodes(data.nodes || []);
        setEdges(data.edges || []);
        setDiagramType(data.diagramType || 'flowchart');
      } catch {
        // TODO: afficher une erreur
      }
    };
    reader.readAsText(file);
  };

  // Drag & drop depuis la palette
  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    const type = event.dataTransfer.getData('application/block-type');
    if (!type) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const position = {
      x: event.clientX - bounds.left,
      y: event.clientY - bounds.top,
    };
    const newId = (nodes.length + 1).toString();
    setPendingNode({ id: newId, type, position });
    setShowFrameworkModal(true);
  };
  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
  };
  // Ajout d'un bloc depuis la palette (drag & drop) : toujours type 'editable' + onRename
  const handleFrameworkSelect = (framework: string) => {
    if (!pendingNode) return;
    let label = `${t(pendingNode.type)} (${t(framework)})`;
    if (pendingNode.type === 'custom') {
      const customName = window.prompt(t('customBlockPrompt', 'Nom du bloc personnalisé ?'));
      if (customName) label = customName;
    }
    setNodes((nds) => [
      ...nds,
      {
        id: pendingNode.id,
        position: pendingNode.position,
        data: { label, type: pendingNode.type, framework, onRename: handleRenameNode },
        type: 'editable',
      },
    ]);
    setShowFrameworkModal(false);
    setPendingNode(null);
    setSelectedFramework('');
  };

  // Gestion du renommage de node
  const handleRenameNode = (id: string, newLabel: string) => {
    setNodes((nds) => nds.map((n) => n.id === id ? { ...n, data: { ...n.data, label: newLabel, onRename: handleRenameNode } } : n));
  };

  // Gestion du label d'edge
  const handleEdgeLabelChange = (id: string, newLabel: string) => {
    setEdges((eds) => eds.map((e) => e.id === id ? { ...e, data: { ...e.data, label: newLabel }, onEdgeLabelChange: handleEdgeLabelChange } : e));
  };

  // Handler robuste pour changer de diagramme et reset le node initial avec le bon label
  const handleNewDiagram = (type: 'flowchart' | 'architecture' | 'mockup') => {
    setDiagramType(type);
    setNodes([
      { id: '1', position: { x: 250, y: 5 }, data: { label: getNodeLabel(type), onRename: handleRenameNode }, type: 'editable', selected: false }
    ]);
    setEdges([]);
    setShowFrameworkModal(false);
    setPendingNode(null);
    setSelectedFramework('');
  };

  // Fonction utilitaire pour obtenir le label du node initial selon le type de diagramme
  const getNodeLabel = (type: 'flowchart' | 'architecture' | 'mockup') => {
    if (type === 'flowchart') return t('newFlowchart');
    if (type === 'architecture') return t('newArchitectureDiagram');
    if (type === 'mockup') return t('newMockup');
    return '';
  };

  // SUPPRIME le useEffect qui patchait le label du node initial

  // ReactFlow multi-select: active la sélection multiple avec shift/cmd/ctrl
  // (ReactFlow gère nativement la sélection multiple si multiSelectionKeyCode est défini)
  // On peut aussi forcer l'option si besoin :
  const reactFlowProps = {
    multiSelectionKeyCode: ['Shift', 'Meta', 'Control'],
    // ...autres props ReactFlow si besoin...
  };

  // Palette repliable/dépliable sur hover, prend toute la taille de la frame de dessin
  const [paletteHovered, setPaletteHovered] = React.useState(false);

  return (
    <Card className="p-6 flex flex-col gap-4 h-full flex-1 relative">
      <h2 className="text-2xl font-bold mb-2">🎨 {t('title')}</h2>
      <p className="mb-2">{t('description')}</p>
      <div className="flex gap-2 mb-2">
        {(['flowchart', 'architecture', 'mockup'] as const).map((type) => (
          <Button
            key={type}
            variant="outline"
            onClick={() => handleNewDiagram(type)}
            className={diagramType === type ? 'bg-primary/80 text-primary-foreground hover:bg-primary/90' : ''}
            style={diagramType === type ? { boxShadow: '0 2px 8px 0 rgba(80,80,255,0.10)' } : {}}
          >
            {t(type === 'flowchart' ? 'newFlowchart' : type === 'architecture' ? 'newArchitectureDiagram' : 'newMockup')}
          </Button>
        ))}
        <Button variant="outline" onClick={handleAddNode}>{t('addBlock', 'Ajouter un bloc')}</Button>
        <input type="file" ref={fileInputRef} style={{ display: 'none' }} accept=".js,.ts,.txt" onChange={handleImportCode} />
        <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>{t('reverse')}</Button>
        <Button variant="outline" onClick={handleExportCode}>{t('exportCode')}</Button>
        <Button variant="outline" onClick={handleSave}>{t('save')}</Button>
        <input type="file" ref={loadInputRef} style={{ display: 'none' }} accept=".json" onChange={handleLoad} />
        <Button variant="outline" onClick={() => loadInputRef.current?.click()}>{t('load')}</Button>
      </div>
      <div className="flex-1 min-h-[400px] border rounded bg-muted/30 text-muted-foreground overflow-hidden relative">
        {/* Palette repliable animée sur hover, prend toute la taille de la frame de dessin */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            zIndex: 20,
            pointerEvents: 'none', // palette n'intercepte pas les events par défaut
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'flex-end',
            transition: 'background 0.3s',
            background: paletteHovered ? 'rgba(24,24,27,0.10)' : 'transparent',
          }}
          onMouseEnter={() => setPaletteHovered(true)}
          onMouseLeave={() => setPaletteHovered(false)}
        >
          <div
            style={{
              margin: 24,
              width: paletteHovered ? 360 : 56,
              maxWidth: '50vw',
              height: paletteHovered ? '90%' : 56,
              minHeight: 56,
              maxHeight: '90vh',
              opacity: paletteHovered ? 1 : 0.7,
              transform: paletteHovered ? 'scale(1)' : 'scale(0.98)',
              filter: paletteHovered ? 'blur(0px)' : 'none',
              transition: 'all 0.35s cubic-bezier(.4,0,.2,1)',
              boxShadow: paletteHovered ? '0 8px 32px 0 rgba(0,0,0,0.18)' : '0 2px 8px 0 rgba(0,0,0,0.10)',
              borderRadius: 16,
              overflow: 'hidden',
              background: 'linear-gradient(135deg, var(--palette-bg-1, #18181b99) 0%, var(--palette-bg-2, #27272a99) 100%)',
              backdropFilter: paletteHovered ? 'blur(12px)' : 'none',
              WebkitBackdropFilter: paletteHovered ? 'blur(12px)' : 'none',
              border: '1.5px solid var(--palette-border, #27272a66)',
              display: 'flex',
              flexDirection: 'column',
              cursor: paletteHovered ? 'default' : 'pointer',
              pointerEvents: paletteHovered ? 'auto' : 'none',
            }}
          >
            <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'flex-start', pointerEvents: paletteHovered ? 'auto' : 'none' }}>
              <VisualProgrammingPalette compact={!paletteHovered} />
            </div>
          </div>
        </div>
        {/* MiniMap alignée précisément à côté du bloc de zoom (Controls) */}
        <ReactFlow
          key={diagramType}
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView={diagramType}
          edgeTypes={edgeTypes}
          nodeTypes={nodeTypes}
          {...reactFlowProps}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        >
          <Controls />
          <MiniMap style={{ position: 'absolute', left: 40, width: 180, height: 120, zIndex: 11, background: 'rgba(255,255,255,0.9)', borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }} />
          <Background />
        </ReactFlow>
      </div>
      <Dialog open={showFrameworkModal} onOpenChange={setShowFrameworkModal}>
        <DialogContent>
          <DialogTitle>{t('chooseFramework')}</DialogTitle>
          <DialogDescription>{t('chooseFrameworkDesc', 'Sélectionnez le framework ou la technologie pour ce bloc.')}</DialogDescription>
          {pendingNode && (
            <Select value={selectedFramework} onValueChange={(fw) => {
              setSelectedFramework(fw);
              handleFrameworkSelect(fw);
            }}>
              <SelectTrigger>{selectedFramework ? t(selectedFramework) : t('chooseFramework')}</SelectTrigger>
              <SelectContent>
                {FRAMEWORKS[pendingNode.type]?.map((fw) => (
                  <SelectItem key={fw.value} value={fw.value}>{t(fw.labelKey)}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
};