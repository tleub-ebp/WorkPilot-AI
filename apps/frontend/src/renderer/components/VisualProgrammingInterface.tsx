import React, { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Card } from './ui/card';
import { Button } from './ui/button';
import ReactFlow, { MiniMap, Controls, Background, addEdge, useNodesState, useEdgesState, Connection, Edge } from 'reactflow';
import 'reactflow/dist/style.css';
import { VisualProgrammingPalette } from './VisualProgrammingPalette';
import { Dialog, DialogContent, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Select, SelectItem, SelectTrigger, SelectContent } from './ui/select';
import { nodeTypes, edgeTypes } from './reactflowTypes';
import { toast } from "../hooks/use-toast";
import { FileTree } from './FileTree';
import { useSettingsStore } from '../stores/settings-store';

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
  const reactFlowRef = useRef<any>(null);
  const [isJsonSaved, setIsJsonSaved] = useState(true);
  const [selectedFolder, setSelectedFolder] = useState<string>("");
  const [showSaveAsDialog, setShowSaveAsDialog] = useState(false);
  const [saveAsFileName, setSaveAsFileName] = useState("");
  const projectRoot = window.electronAPI?.getProjectRoot?.() || "";
  const theme = useSettingsStore((state) => state.settings.theme);

  // Frameworks par type
  const FRAMEWORKS: Record<string, { value: string; labelKey: string }[]> = {
    frontend: [
      { value: 'React', labelKey: 'React' },
      { value: 'Angular', labelKey: 'Angular' },
      { value: 'Vue', labelKey: 'Vue' },
      { value: 'Svelte', labelKey: 'Svelte' },
    ],
    backend: [
      { value: 'NodeJs', labelKey: 'NodeJs' },
      { value: 'Python', labelKey: 'Python' },
      { value: 'DotNet', labelKey: '.Net' },
      { value: 'Django', labelKey: 'Django' },
      { value: 'Flask', labelKey: 'Flask' },
      { value: 'Spring', labelKey: 'Spring' },
    ],
    database: [
      { value: 'Postgres', labelKey: 'Postgres' },
      { value: 'MySql', labelKey: 'MySql' },
      { value: 'MongoDb', labelKey: 'MongoDb' },
      { value: 'Sqlite', labelKey: 'Sqlite' },
    ],
    api: [
      { value: 'Rest', labelKey: 'Rest' },
      { value: 'Graphql', labelKey: 'Graphql' },
      { value: 'Grpc', labelKey: 'Grpc' },
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
    // Export du diagramme au format JSON moderne
    const exportData = {
      nodes,
      edges,
      diagramType,
      exportedAt: new Date().toISOString(),
    };
    // Ajout de l'heure à la milliseconde dans le nom du fichier exporté
    const now = new Date();
    const pad = (n: number, l: number = 2) => n.toString().padStart(l, '0');
    const fileName = `${diagramType}-export-${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}-${pad(now.getMilliseconds(),3)}.json`;
    saveAs(new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' }), fileName);
  };

  const handleImportCode = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    // Utilise Blob#text() pour lire le contenu
    const content = await file.text();
    // Simple heuristique : chaque ligne devient un node, liens entre nodes
    const lines = content.split('\n').filter(l => l.trim());
    const importedNodes = lines.map((line, idx) => ({
      id: `imported-${idx+1}`,
      position: { x: 100 + idx*60, y: 100 + idx*40 },
      data: { label: line },
      type: 'default'
    }));
    const importedEdges = lines.length > 1 ? lines.slice(1).map((_, idx) => ({
      id: `imported-edge-${idx+1}`,
      source: `imported-${idx+1}`,
      target: `imported-${idx+2}`,
      data: { label: '' }
    })) : [];
    setNodes(importedNodes);
    setEdges(importedEdges);
  };

  // Persistance locale (sauvegarde/chargement)
  const handleSave = () => {
    // Propose une modale avec le nom par défaut (timestamp)
    setSaveAsFileName(getDefaultFileName());
    setShowSaveAsDialog(true);
  };

  // Génère le nom par défaut avec timestamp
  const getDefaultFileName = () => {
    const now = new Date();
    const pad = (n: number, l: number = 2) => n.toString().padStart(l, '0');
    return `${getDiagramPrefix(diagramType)}-export-${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}-${pad(now.getMilliseconds(),3)}.json`;
  };

  // Handler pour effectuer la sauvegarde avec le nom choisi
  const confirmSaveAs = async () => {
    const exportData = {
      nodes,
      edges,
      diagramType,
      exportedAt: new Date().toISOString(),
    };
    const fileName = saveAsFileName;
    const folderPath = selectedFolder;
    try {
      const result = await window.electronAPI.saveJsonFile(folderPath, fileName, exportData);
      if (result?.success) {
        setIsJsonSaved(true);
        setShowSaveAsDialog(false);
        toast({
          variant: theme || 'default',
          title: t('saveSuccess', 'Sauvegarde réussie'),
          description: `${t('fileSavedIn', 'Fichier sauvegardé dans')} ${folderPath}`,
          variant: 'success',
        });
        // Suppression de l'appel direct à handleNewDiagram(nextDiagramType)
      } else {
        toast({
          title: t('saveError', 'Erreur lors de la sauvegarde'),
          description: result?.error || 'Erreur inconnue',
        });
      }
    } catch (e) {
      toast({ title: t('saveError', 'Erreur lors de la sauvegarde'), description: e.message });
    }
  };

  // Handler pour annuler la sauvegarde et changer de diagramme
  const cancelSaveAs = () => {
    setShowSaveAsDialog(false);
    setNextDiagramType(null);
  };

  const handleLoad = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      // Utilise Blob#text() pour lire le contenu
      const content = await file.text();
      const data = JSON.parse(content);
      setNodes(data.nodes || []);
      setEdges(data.edges || []);
      setDiagramType(data.diagramType || 'flowchart');
    } catch {
      toast({
        title: t('loadErrorTitle', 'Erreur de chargement'),
        description: t('loadErrorDesc', 'Le fichier est invalide ou corrompu.'),
        variant: 'destructive',
      });
    }
  };

  // Correction du drop : position exacte sous la souris
  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    const type = event.dataTransfer.getData('application/block-type');
    if (!type) return;
    const reactFlowInstance = reactFlowRef.current;
    const bounds = event.currentTarget.getBoundingClientRect();
    // Coordonnées du curseur par rapport au conteneur ReactFlow
    const mouseX = event.clientX - bounds.left;
    const mouseY = event.clientY - bounds.top;
    // Conversion en coordonnées diagramme
    let position = { x: mouseX, y: mouseY };
    if (reactFlowInstance && reactFlowInstance.project) {
      position = reactFlowInstance.project({ x: mouseX, y: mouseY });
    }
    if (!FRAMEWORKS[type]) {
      const newId = (nodes.length + 1).toString();
      setNodes((nds) => [
        ...nds,
        {
          id: newId,
          position,
          data: { label: type.charAt(0).toUpperCase() + type.slice(1), type, onRename: handleRenameNode },
          type: 'editable',
        },
      ]);
    } else {
      const newId = (nodes.length + 1).toString();
      setPendingNode({ id: newId, type, position });
      setShowFrameworkModal(true);
    }
  };
  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
  };
  // Ajout d'un bloc depuis la palette (drag & drop) : toujours type 'editable' + onRename
  const handleFrameworkSelect = (framework: string) => {
    if (!pendingNode) return;

    const pascalType = pendingNode.type.charAt(0).toUpperCase() + pendingNode.type.slice(1);
    let label = `${framework} (${pascalType})`;
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

  const [nextDiagramType, setNextDiagramType] = useState<'flowchart' | 'architecture' | 'mockup' | null>(null);

  // Handler pour demander confirmation
  const requestDiagramChange = (type: 'flowchart' | 'architecture' | 'mockup') => {
    setNextDiagramType(type);
    setShowSaveAsDialog(true);
  };

  // Handler robuste pour changer de diagramme et reset le node initial avec le bon label
  const handleNewDiagram = (type: 'flowchart' | 'architecture' | 'mockup') => {
    if (!isJsonSaved) {
      setNextDiagramType(type);
      setShowSaveAsDialog(true);
      return;
    }
    setDiagramType(type);
    setNodes([
      { id: '1', position: { x: 250, y: 5 }, data: { label: getNodeLabel(type), onRename: handleRenameNode }, type: 'editable', selected: false }
    ]);
    setEdges([]);
    setShowFrameworkModal(false);
    setPendingNode(null);
    setSelectedFramework('');
    setNextDiagramType(null);
    setIsJsonSaved(false);
  };

  // Fonction utilitaire pour obtenir le label du node initial selon le type de diagramme
  const getNodeLabel = (type: 'flowchart' | 'architecture' | 'mockup') => {
    if (type === 'flowchart') return t('newFlowchart');
    if (type === 'architecture') return t('newArchitectureDiagram');
    if (type === 'mockup') return t('newMockup');
    return '';
  };

  const getDiagramPrefix = (type: string) => {
    if (type === 'architecture') return 'architectural';
    if (type === 'flowchart') return 'organigramme';
    if (type === 'mockup') return 'mockup';
    return 'diagram';
  };

  // ReactFlow multi-select: active la sélection multiple avec shift/cmd/ctrl
  // (ReactFlow gère nativement la sélection multiple si multiSelectionKeyCode est défini)
  // On peut aussi forcer l'option si besoin :
  const reactFlowProps = {
    multiSelectionKeyCode: ['Shift', 'Meta', 'Control'],
    // ...autres props ReactFlow si besoin...
  };

  // Suppression des nodes/edges sélectionnés via la touche Suppr
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        setNodes((nds) => nds.filter((n) => !n.selected));
        setEdges((eds) => eds.filter((e) => !e.selected));
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setNodes, setEdges]);

  // Handler pour changer de diagramme après la sauvegarde ou annulation
  React.useEffect(() => {
    if (!showSaveAsDialog && nextDiagramType !== null) {
      handleNewDiagram(nextDiagramType);
      setNextDiagramType(null);
    }
  }, [showSaveAsDialog, nextDiagramType]);

  // Handler pour ouvrir la modale Save As
  const handleSaveAs = () => {
    setSaveAsFileName(getDefaultFileName());
    setShowSaveAsDialog(true);
  };

  // Handler pour confirmation sauvegarde puis changement de diagramme
  const handleSaveAndChangeDiagram = () => {
    setNextDiagramType(nextDiagramType);
    setSaveAsFileName(getDefaultFileName());
    setShowSaveAsDialog(true);
  };

  // Handler pour changer sans enregistrer
  const handleChangeDiagramWithoutSave = () => {
    setNextDiagramType(nextDiagramType);
    setShowSaveAsDialog(false);
  };

  const handleNodesChange = (changes: any) => {
    setIsJsonSaved(false);
    onNodesChange(changes);
  };
  const handleEdgesChange = (changes: any) => {
    setIsJsonSaved(false);
    onEdgesChange(changes);
  };

  // Correction : fallback dynamique pour explorerRoot si getUserHome échoue
  const getDefaultExplorerRoot = () => {
    const home = window.electronAPI?.getUserHome?.();
    if (home && typeof home === 'string' && home.length > 0) return home;
    // Fallback Windows
    if (window.process?.platform === 'win32') return 'C:\\';
    // Fallback Unix
    return '/';
  };
  const [explorerRoot, setExplorerRoot] = useState(getDefaultExplorerRoot());
  // Ajout d'un état temporaire pour la saisie du chemin
  const [explorerRootInput, setExplorerRootInput] = useState(explorerRoot);

  // Remplir automatiquement le champ du nom de fichier avec la suggestion par défaut lors de l'ouverture de la popin
  React.useEffect(() => {
    if (showSaveAsDialog) {
      setSaveAsFileName(getDefaultFileName());
    }
  }, [showSaveAsDialog]);

  // Validation assouplie pour Windows et Unix
  const isValidPath = (path: string) => {
    if (!path || typeof path !== 'string') return false;
    // Windows : accepte tout chemin commençant par une lettre suivie de :\ ou \\ (UNC)
    if (window.process?.platform === 'win32') {
      return /^[A-Za-z]:\\/.test(path) || /^\\\\/.test(path);
    }
    // Unix : accepte tout chemin commençant par /
    return path.startsWith('/');
  };

  return (
    <Card className="p-6 flex flex-col gap-4 h-full flex-1 relative">
      <h2 className="text-2xl font-bold mb-2">🎨 {t('title')}</h2>
      <p className="mb-2">{t('description')}</p>
      {/* Zone principale avec boutons de programmation visuelle */}
      <div className="flex flex-col h-full">
        <div className="flex gap-2 mb-2">
          {(['flowchart', 'architecture', 'mockup'] as const).map((type) => (
            <Button
              key={type}
              variant="outline"
              onClick={() => requestDiagramChange(type)}
              className={diagramType === type ? 'bg-primary/80 text-primary-foreground hover:bg-primary/90' : ''}
              style={diagramType === type ? { boxShadow: '0 2px 8px 0 rgba(80,80,255,0.10)' } : {}}
            >
              {t(type === 'flowchart' ? 'newFlowchart' : type === 'architecture' ? 'newArchitectureDiagram' : 'newMockup')}
            </Button>
          ))}
          <Button variant="outline" onClick={handleAddNode}>{t('addBlock', 'Ajouter un bloc')}</Button>
          <input type="file" ref={fileInputRef} style={{ display: 'none' }} accept=".js,.ts,.txt" onChange={handleImportCode} />
          <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>{t('reverse')}</Button>
          <Button variant="outline" onClick={handleExportCode}>{t('save', 'Enregistrer')}</Button>
          <Button variant="outline" onClick={handleSaveAs}>{t('save', 'Enregistrer')}</Button>
          <input type="file" ref={loadInputRef} style={{ display: 'none' }} accept=".json" onChange={handleLoad} />
          <Button variant="outline" onClick={() => loadInputRef.current?.click()}>{t('load')}</Button>
        </div>
        <div className="flex-1 min-h-[400px] border rounded bg-muted/30 text-muted-foreground overflow-hidden relative">
          <ReactFlow
            ref={reactFlowRef}
            key={diagramType}
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
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

      {/* Modale Save As */}
      <Dialog open={showSaveAsDialog} onOpenChange={setShowSaveAsDialog}>
        <DialogContent>
          <DialogTitle>{t('chooseFileName', 'Nom du fichier d’export')}</DialogTitle>
          <div className="mt-4">
            <DialogDescription>{t('chooseFileNameDesc', 'Vous pouvez modifier le nom du fichier avant l’enregistrement.')}</DialogDescription>
          </div>
          <div className="mt-4">
            <label className="block text-xs font-bold mb-1">{t('explorerRoot', 'Racine de l\'explorateur :')}</label>
            <div className="flex gap-2">
              <input
                  type="text"
                  value={explorerRootInput}
                  onChange={e => setExplorerRootInput(e.target.value)}
                  className="w-full p-2 border rounded"
                  placeholder="C:\\ ou /"
              />
              <Button variant="secondary" onClick={() => setExplorerRoot(explorerRootInput)} disabled={explorerRootInput.length === 0}>
                {t('selectFolder', 'Sélectionner')}
              </Button>
            </div>
          </div>
          <div className="mt-4" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
            <FileTree rootPath={explorerRoot} onSelectFolder={setSelectedFolder} selectedFolder={selectedFolder} />
            <div className="mt-2 text-sm font-bold text-primary">
              Dossier sélectionné : {selectedFolder || 'Aucun'}
            </div>
          </div>
          <div className="mt-4">
            <label className="block text-xs font-bold mb-1">{t('fileNameLabel', 'Nom du fichier :')}</label>
            <input
              type="text"
              value={saveAsFileName}
              onChange={e => setSaveAsFileName(e.target.value)}
              className="w-full mt-1 p-2 border rounded"
              placeholder={getDefaultFileName()}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={confirmSaveAs} disabled={!selectedFolder || !saveAsFileName || saveAsFileName.trim().length === 0}>
              {t('save', 'Sauvegarder dans le dossier sélectionné')}
            </Button>
            <Button variant="ghost" onClick={cancelSaveAs}>{t('cancel', 'Annuler')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
};
