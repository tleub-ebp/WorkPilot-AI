#!/usr/bin/env python3
"""
Angular Component Generator

Generates Angular components, services, and other artifacts with best practices.
Supports both standalone and module-based components with modern Angular patterns.
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ComponentGenerationOptions:
    """Options for component generation."""
    name: str
    type: str = "component"  # component, service, directive, pipe, guard
    standalone: bool = True
    path: str = "src/app"
    prefix: str = "app"
    inline_template: bool = False
    inline_style: bool = False
    style_ext: str = "css"  # css, scss, sass, less, styl
    skip_tests: bool = False
    skip_selector: bool = False
    selector: Optional[str] = None
    implements: List[str] = None  # OnInit, OnDestroy, etc.
    exports: bool = False
    change_detection: str = "Default"  # Default, OnPush


@dataclass
class GenerationResult:
    """Result of component generation."""
    success: bool
    files_created: List[str]
    files_updated: List[str]
    warnings: List[str]
    errors: List[str]
    next_steps: List[str]


class AngularComponentGenerator:
    """Generates Angular artifacts with modern best practices."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.templates_dir = Path(__file__).parent.parent / "templates"
        
    def generate(self, options: ComponentGenerationOptions) -> GenerationResult:
        """Generate Angular component or other artifact."""
        result = GenerationResult(
            success=False,
            files_created=[],
            files_updated=[],
            warnings=[],
            errors=[],
            next_steps=[]
        )
        
        try:
            # Validate input
            if not self._validate_options(options, result):
                return result
            
            # Determine file paths
            file_paths = self._get_file_paths(options)
            
            # Generate files based on type
            if options.type == "component":
                self._generate_component(options, file_paths, result)
            elif options.type == "service":
                self._generate_service(options, file_paths, result)
            elif options.type == "directive":
                self._generate_directive(options, file_paths, result)
            elif options.type == "pipe":
                self._generate_pipe(options, file_paths, result)
            elif options.type == "guard":
                self._generate_guard(options, file_paths, result)
            else:
                result.errors.append(f"Unsupported type: {options.type}")
                return result
            
            # Update module if not standalone
            if not options.standalone and options.type == "component":
                self._update_module(options, result)
            
            result.success = True
            self._add_next_steps(options, result)
            
        except Exception as e:
            result.errors.append(f"Generation failed: {str(e)}")
        
        return result
    
    def _validate_options(self, options: ComponentGenerationOptions, result: GenerationResult) -> bool:
        """Validate generation options."""
        if not options.name or not re.match(r'^[a-zA-Z][a-zA-Z0-9]*$', options.name):
            result.errors.append("Invalid component name. Use camelCase starting with a letter.")
            return False
        
        if options.type not in ["component", "service", "directive", "pipe", "guard"]:
            result.errors.append(f"Unsupported type: {options.type}")
            return False
        
        if options.style_ext not in ["css", "scss", "sass", "less", "styl"]:
            result.errors.append(f"Unsupported style extension: {options.style_ext}")
            return False
        
        return True
    
    def _get_file_paths(self, options: ComponentGenerationOptions) -> Dict[str, Path]:
        """Get file paths for the generated artifact."""
        base_name = self._kebab_case(options.name)
        target_dir = self.project_root / options.path
        
        paths = {
            "base_dir": target_dir / base_name,
            "component_ts": target_dir / f"{base_name}.component.ts",
            "component_html": target_dir / f"{base_name}.component.html",
            "component_style": target_dir / f"{base_name}.component.{options.style_ext}",
            "component_spec": target_dir / f"{base_name}.component.spec.ts",
            "service_ts": target_dir / f"{base_name}.service.ts",
            "service_spec": target_dir / f"{base_name}.service.spec.ts",
            "directive_ts": target_dir / f"{base_name}.directive.ts",
            "directive_spec": target_dir / f"{base_name}.directive.spec.ts",
            "pipe_ts": target_dir / f"{base_name}.pipe.ts",
            "pipe_spec": target_dir / f"{base_name}.pipe.spec.ts",
            "guard_ts": target_dir / f"{base_name}.guard.ts",
            "guard_spec": target_dir / f"{base_name}.guard.spec.ts"
        }
        
        return paths
    
    def _generate_component(self, options: ComponentGenerationOptions, file_paths: Dict[str, Path], result: GenerationResult):
        """Generate Angular component files."""
        # Create directory if needed
        file_paths["base_dir"].mkdir(parents=True, exist_ok=True)
        
        # Generate TypeScript file
        component_content = self._get_component_template(options)
        self._write_file(file_paths["component_ts"], component_content, result)
        
        # Generate HTML template
        if not options.inline_template:
            html_content = self._get_html_template(options)
            self._write_file(file_paths["component_html"], html_content, result)
        
        # Generate styles
        if not options.inline_style:
            style_content = self._get_style_template(options)
            self._write_file(file_paths["component_style"], style_content, result)
        
        # Generate test file
        if not options.skip_tests:
            test_content = self._get_component_test_template(options)
            self._write_file(file_paths["component_spec"], test_content, result)
    
    def _generate_service(self, options: ComponentGenerationOptions, file_paths: Dict[str, Path], result: GenerationResult):
        """Generate Angular service files."""
        # Create directory if needed
        file_paths["base_dir"].mkdir(parents=True, exist_ok=True)
        
        # Generate service file
        service_content = self._get_service_template(options)
        self._write_file(file_paths["service_ts"], service_content, result)
        
        # Generate test file
        if not options.skip_tests:
            test_content = self._get_service_test_template(options)
            self._write_file(file_paths["service_spec"], test_content, result)
    
    def _generate_directive(self, options: ComponentGenerationOptions, file_paths: Dict[str, Path], result: GenerationResult):
        """Generate Angular directive files."""
        file_paths["base_dir"].mkdir(parents=True, exist_ok=True)
        
        directive_content = self._get_directive_template(options)
        self._write_file(file_paths["directive_ts"], directive_content, result)
        
        if not options.skip_tests:
            test_content = self._get_directive_test_template(options)
            self._write_file(file_paths["directive_spec"], test_content, result)
    
    def _generate_pipe(self, options: ComponentGenerationOptions, file_paths: Dict[str, Path], result: GenerationResult):
        """Generate Angular pipe files."""
        file_paths["base_dir"].mkdir(parents=True, exist_ok=True)
        
        pipe_content = self._get_pipe_template(options)
        self._write_file(file_paths["pipe_ts"], pipe_content, result)
        
        if not options.skip_tests:
            test_content = self._get_pipe_test_template(options)
            self._write_file(file_paths["pipe_spec"], test_content, result)
    
    def _generate_guard(self, options: ComponentGenerationOptions, file_paths: Dict[str, Path], result: GenerationResult):
        """Generate Angular guard files."""
        file_paths["base_dir"].mkdir(parents=True, exist_ok=True)
        
        guard_content = self._get_guard_template(options)
        self._write_file(file_paths["guard_ts"], guard_content, result)
        
        if not options.skip_tests:
            test_content = self._get_guard_test_template(options)
            self._write_file(file_paths["guard_spec"], test_content, result)
    
    def _get_component_template(self, options: ComponentGenerationOptions) -> str:
        """Get component TypeScript template."""
        class_name = self._pascal_case(options.name)
        selector = options.selector or f"{options.prefix}-{self._kebab_case(options.name)}"
        
        imports = []
        decorators = []
        class_implements = []
        
        # Add imports based on implements
        if options.implements:
            for impl in options.implements:
                if impl == "OnInit":
                    imports.append("OnInit")
                    class_implements.append("OnInit")
                elif impl == "OnDestroy":
                    imports.append("OnDestroy")
                    class_implements.append("OnDestroy")
                elif impl == "AfterViewInit":
                    imports.append("AfterViewInit")
                    class_implements.append("AfterViewInit")
        
        # Build import statement
        import_statement = ""
        if imports:
            import_statement = f"import {{ {', '.join(imports)} }} from '@angular/core';"
        
        # Build implements statement
        implements_statement = ""
        if class_implements:
            implements_statement = f" implements {', '.join(class_implements)}"
        
        # Build template and style
        template_attr = ""
        if options.inline_template:
            template_attr = f'\n  template: `<div class="{self._kebab_case(options.name)}">\n    <p>{class_name} works!</p>\n  </div>`,'
        else:
            template_attr = f'\n  templateUrl: "./{self._kebab_case(options.name)}.component.html",'
        
        style_attr = ""
        if options.inline_style:
            style_attr = f'\n  styles: [`.{self._kebab_case(options.name)} {{\n    padding: 20px;\n  }}`],'
        else:
            style_attr = f'\n  styleUrls: ["./{self._kebab_case(options.name)}.component.{options.style_ext}"],'
        
        # Change detection
        cd_strategy = f"ChangeDetectionStrategy.{options.change_detection}"
        
        # Standalone imports
        standalone_imports = ""
        if options.standalone:
            standalone_imports = f"\n  standalone: true,"
            if options.inline_template:
                standalone_imports += f"\n  imports: [CommonModule],"
            else:
                standalone_imports += f"\n  imports: [CommonModule],"
        
        template = f'''import {{ Component }} from '@angular/core';
{import_statement}
import {{ CommonModule }} from '@angular/common';

@Component({{
  selector: '{selector}',{template_attr}{style_attr}
  changeDetection: ChangeDetectionStrategy.{options.change_detection},{standalone_imports}
}})
export class {class_name}Component{implements_statement} {{
  
  constructor() {{}}
  
{self._generate_lifecycle_methods(options.implements)}
}}'''
        
        return template
    
    def _get_html_template(self, options: ComponentGenerationOptions) -> str:
        """Get HTML template for component."""
        class_name = self._pascal_case(options.name)
        kebab_name = self._kebab_case(options.name)
        
        return f'''<div class="{kebab_name}">
  <h2>{class_name}</h2>
  <p>This is the {class_name} component.</p>
</div>'''
    
    def _get_style_template(self, options: ComponentGenerationOptions) -> str:
        """Get style template for component."""
        kebab_name = self._kebab_case(options.name)
        
        return f'''.{kebab_name} {{
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 4px;
  margin: 10px 0;
}}

.{kebab_name} h2 {{
  color: #333;
  margin-top: 0;
}}'''
    
    def _get_component_test_template(self, options: ComponentGenerationOptions) -> str:
        """Get test template for component."""
        class_name = self._pascal_case(options.name)
        kebab_name = self._kebab_case(options.name)
        
        return f'''import {{ ComponentFixture, TestBed }} from '@angular/core/testing';

import {{ {class_name}Component }} from './{kebab_name}.component';

describe('{class_name}Component', () => {{
  let component: {class_name}Component;
  let fixture: ComponentFixture<{class_name}Component>;

  beforeEach(async () => {{
    await TestBed.configureTestingModule({{
      imports: [{class_name}Component]
    }})
    .compileComponents();

    fixture = TestBed.createComponent({class_name}Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }});

  it('should create', () => {{
    expect(component).toBeTruthy();
  }});

  it('should render title', () => {{
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('h2')?.textContent).toContain('{class_name}');
  }});
}});'''
    
    def _get_service_template(self, options: ComponentGenerationOptions) -> str:
        """Get service template."""
        class_name = self._pascal_case(options.name)
        
        return f'''import {{ Injectable }} from '@angular/core';

@Injectable({{
  providedIn: 'root'
}})
export class {class_name}Service {{
  
  constructor() {{}}
  
  // Add your service methods here
}}'''
    
    def _get_service_test_template(self, options: ComponentGenerationOptions) -> str:
        """Get service test template."""
        class_name = self._pascal_case(options.name)
        
        return f'''import {{ TestBed }} from '@angular/core/testing';

import {{ {class_name}Service }} from './{options.name}.service';

describe('{class_name}Service', () => {{
  let service: {class_name}Service;

  beforeEach(() => {{
    TestBed.configureTestingModule({{}});
    service = TestBed.inject({class_name}Service);
  }});

  it('should be created', () => {{
    expect(service).toBeTruthy();
  }});
}});'''
    
    def _get_directive_template(self, options: ComponentGenerationOptions) -> str:
        """Get directive template."""
        class_name = self._pascal_case(options.name)
        selector = options.selector or f"[{options.prefix}{self._kebab_case(options.name)}]"
        
        return f'''import {{ Directive }} from '@angular/core';

@Directive({{
  selector: '{selector}',
  standalone: true
}})
export class {class_name}Directive {{
  
  constructor() {{}}
}}'''
    
    def _get_directive_test_template(self, options: ComponentGenerationOptions) -> str:
        """Get directive test template."""
        class_name = self._pascal_case(options.name)
        
        return f'''import {{ {class_name}Directive }} from './{options.name}.directive';

describe('{class_name}Directive', () => {{
  it('should create an instance', () => {{
    const directive = new {class_name}Directive();
    expect(directive).toBeTruthy();
  }});
}});'''
    
    def _get_pipe_template(self, options: ComponentGenerationOptions) -> str:
        """Get pipe template."""
        class_name = self._pascal_case(options.name)
        pipe_name = self._kebab_case(options.name)
        
        return f'''import {{ Pipe, PipeTransform }} from '@angular/core';

@Pipe({{
  name: '{pipe_name}',
  standalone: true
}})
export class {class_name}Pipe implements PipeTransform {{
  
  transform(value: unknown, ...args: unknown[]): unknown {{
    // Add your pipe logic here
    return value;
  }}
}}'''
    
    def _get_pipe_test_template(self, options: ComponentGenerationOptions) -> str:
        """Get pipe test template."""
        class_name = self._pascal_case(options.name)
        
        return f'''import {{ {class_name}Pipe }} from './{options.name}.pipe';

describe('{class_name}Pipe', () => {{
  it('create an instance', () => {{
    const pipe = new {class_name}Pipe();
    expect(pipe).toBeTruthy();
  }});
}});'''
    
    def _get_guard_template(self, options: ComponentGenerationOptions) -> str:
        """Get guard template."""
        class_name = self._pascal_case(options.name)
        
        return f'''import {{ Injectable }} from '@angular/core';
import {{ CanActivate, Router }} from '@angular/router';

@Injectable({{
  providedIn: 'root'
}})
export class {class_name}Guard implements CanActivate {{
  
  constructor(private router: Router) {{}}
  
  canActivate(): boolean {{
    // Add your guard logic here
    return true;
  }}
}}'''
    
    def _get_guard_test_template(self, options: ComponentGenerationOptions) -> str:
        """Get guard test template."""
        class_name = self._pascal_case(options.name)
        
        return f'''import {{ TestBed }} from '@angular/core/testing';
import {{ Router }} from '@angular/router';

import {{ {class_name}Guard }} from './{options.name}.guard';

describe('{class_name}Guard', () => {{
  let guard: {class_name}Guard;
  let routerSpy: jasmine.SpyObj<Router>;

  beforeEach(() => {{
    const spy = jasmine.createSpyObj('Router', ['navigate']);
    TestBed.configureTestingModule({{
      providers: [
        {class_name}Guard,
        {{ provide: Router, useValue: spy }}
      ]
    }});
    guard = TestBed.inject({class_name}Guard);
    routerSpy = TestBed.inject(Router) as jasmine.SpyObj<Router>;
  }});

  it('should be created', () => {{
    expect(guard).toBeTruthy();
  }});
}});'''
    
    def _generate_lifecycle_methods(self, implements: List[str]) -> str:
        """Generate lifecycle methods based on implements."""
        methods = []
        
        if "OnInit" in implements:
            methods.append("  ngOnInit(): void {\n    // Add initialization logic here\n  }")
        
        if "OnDestroy" in implements:
            methods.append("  ngOnDestroy(): void {\n    // Add cleanup logic here\n  }")
        
        if "AfterViewInit" in implements:
            methods.append("  ngAfterViewInit(): void {\n    // Add post-view initialization logic here\n  }")
        
        return "\n\n".join(methods) if methods else ""
    
    def _update_module(self, options: ComponentGenerationOptions, result: GenerationResult):
        """Update module file with new component."""
        # This is a placeholder for module update logic
        # Real implementation would find the appropriate module and add the component
        result.warnings.append("Manual module update required - add component to appropriate module")
    
    def _add_next_steps(self, options: ComponentGenerationOptions, result: GenerationResult):
        """Add next steps to the result."""
        if options.type == "component":
            result.next_steps.append(f"Add the component to your routing configuration")
            result.next_steps.append(f"Implement the component's functionality")
            result.next_steps.append(f"Add unit tests for the component")
        
        if not options.standalone:
            result.next_steps.append(f"Add the component to an Angular module")
    
    def _write_file(self, file_path: Path, content: str, result: GenerationResult):
        """Write content to file."""
        try:
            file_path.write_text(content, encoding='utf-8')
            result.files_created.append(str(file_path.relative_to(self.project_root)))
        except Exception as e:
            result.errors.append(f"Failed to write {file_path}: {str(e)}")
    
    def _pascal_case(self, text: str) -> str:
        """Convert text to PascalCase."""
        return ''.join(word.capitalize() for word in text.split('_'))
    
    def _kebab_case(self, text: str) -> str:
        """Convert text to kebab-case."""
        # Convert camelCase to kebab-case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', text)
        return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python generate_component.py <project_root> [options]")
        print("Options should be provided as JSON string")
        print("Example: python generate_component.py /path/to/project '{\"name\":\"UserProfile\",\"type\":\"component\"}'")
        sys.exit(1)
    
    project_root = sys.argv[1]
    
    # Parse options
    options = ComponentGenerationOptions(name="Example")
    
    if len(sys.argv) > 2:
        try:
            options_dict = json.loads(sys.argv[2])
            for key, value in options_dict.items():
                if hasattr(options, key):
                    setattr(options, key, value)
        except json.JSONDecodeError:
            print("Invalid JSON options provided")
            sys.exit(1)
    
    generator = AngularComponentGenerator(project_root)
    
    try:
        result = generator.generate(options)
        
        # Output results as JSON
        output = {
            "success": result.success,
            "files_created": result.files_created,
            "files_updated": result.files_updated,
            "warnings": result.warnings,
            "errors": result.errors,
            "next_steps": result.next_steps
        }
        
        print(json.dumps(output, indent=2))
        
        if not result.success:
            sys.exit(1)
            
    except Exception as e:
        error_output = {
            "success": False,
            "error": str(e),
            "project_root": project_root
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
