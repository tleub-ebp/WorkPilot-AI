"""
Unit tests for migration transformers
Tests individual transformer functionality
"""

import pytest
from pathlib import Path
import tempfile

from apps.backend.migration.transformers.react_to_vue import ReactToVueTransformer
from apps.backend.migration.transformers.database import DatabaseTransformer
from apps.backend.migration.transformers.python import PythonTransformer
from apps.backend.migration.transformers.js_to_ts import JSToTypeScriptTransformer
from tests.migration_fixtures import TEST_FIXTURES


class TestReactToVueTransformer:
    """Test React to Vue transformations."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_detect_react_component(self, temp_project):
        """Test React component detection."""
        transformer = ReactToVueTransformer(temp_project)
        
        react_code = TEST_FIXTURES['react_component']['content']
        assert transformer._is_react_component(react_code)
        
        # Non-React code
        assert not transformer._is_react_component("const x = 5")
    
    def test_transform_jsx_to_template(self, temp_project):
        """Test JSX to template transformation."""
        transformer = ReactToVueTransformer(temp_project)
        
        jsx = '<div className="counter"><p>Count: {count}</p></div>'
        result = transformer._transform_jsx_to_template(jsx)
        
        assert 'class=' in result
        assert 'className=' not in result
        assert '{{ count }}' in result or '{ count }' not in result
    
    def test_transform_event_handlers(self, temp_project):
        """Test event handler transformation."""
        transformer = ReactToVueTransformer(temp_project)
        
        jsx = '<button onClick={handleClick}>Click</button>'
        result = transformer._transform_event_handlers(jsx)
        
        assert '@click=' in result
        assert 'onClick=' not in result
    
    def test_transform_print_statement(self, temp_project):
        """Test print statement transformation."""
        transformer = PythonTransformer(temp_project)
        
        code = 'print "Hello, World!"'
        result = transformer._transform_print_statements(code)
        
        assert 'print(' in result
        assert '"Hello, World!"' in result


class TestDatabaseTransformer:
    """Test MySQL to PostgreSQL transformations."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_type_mappings(self, temp_project):
        """Test data type conversions."""
        transformer = DatabaseTransformer(temp_project)
        
        # Test INT -> INTEGER
        sql = "CREATE TABLE users (id INT NOT NULL AUTO_INCREMENT PRIMARY KEY)"
        result = transformer._transform_sql(sql)
        
        assert 'INTEGER' in result or 'SERIAL' in result
        assert 'INT' not in result or 'INTEGER' in result
    
    def test_remove_mysql_options(self, temp_project):
        """Test removal of MySQL-specific options."""
        transformer = DatabaseTransformer(temp_project)
        
        sql = "CREATE TABLE users (...) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        result = transformer._transform_sql(sql)
        
        assert 'ENGINE' not in result
        assert 'CHARSET' not in result
    
    def test_backtick_replacement(self, temp_project):
        """Test backtick to quote conversion."""
        transformer = DatabaseTransformer(temp_project)
        
        sql = 'CREATE TABLE `users` (`id` INT)'
        result = transformer._transform_create_table(sql)
        
        assert '`' not in result
        assert '"users"' in result
    
    def test_auto_increment_transformation(self, temp_project):
        """Test AUTO_INCREMENT to SERIAL."""
        transformer = DatabaseTransformer(temp_project)
        
        sql = "id INT NOT NULL AUTO_INCREMENT PRIMARY KEY"
        result = transformer._transform_auto_increment(sql)
        
        assert 'SERIAL' in result
        assert 'AUTO_INCREMENT' not in result


class TestPythonTransformer:
    """Test Python 2 to 3 transformations."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_detect_python2_code(self, temp_project):
        """Test Python 2 detection."""
        transformer = PythonTransformer(temp_project)
        
        python2_code = TEST_FIXTURES['python2_code']['content']
        assert transformer._is_python2_code(python2_code)
        
        # Python 3 code
        python3_code = "print('Hello')\nx = range(10)"
        assert not transformer._is_python2_code(python3_code)
    
    def test_xrange_to_range(self, temp_project):
        """Test xrange conversion."""
        transformer = PythonTransformer(temp_project)
        
        code = "for i in xrange(10): pass"
        result = transformer._transform_range(code)
        
        assert 'range(10)' in result
        assert 'xrange' not in result
    
    def test_unicode_to_str(self, temp_project):
        """Test unicode conversion."""
        transformer = PythonTransformer(temp_project)
        
        code = "x = unicode('hello')"
        result = transformer._transform_string_handling(code)
        
        assert "str('hello')" in result
        assert 'unicode' not in result
    
    def test_dict_iteritems(self, temp_project):
        """Test dict.iteritems() conversion."""
        transformer = PythonTransformer(temp_project)
        
        code = "for k, v in mydict.iteritems(): pass"
        result = transformer._transform_iterators(code)
        
        assert '.items()' in result
        assert '.iteritems()' not in result
    
    def test_exception_syntax(self, temp_project):
        """Test exception syntax conversion."""
        transformer = PythonTransformer(temp_project)
        
        code = "except Exception, e:"
        result = transformer._transform_exceptions(code)
        
        assert 'except Exception as e:' in result or 'Exception,' not in result


class TestJSToTypeScriptTransformer:
    """Test JavaScript to TypeScript transformations."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_function_parameter_annotation(self, temp_project):
        """Test function parameter type annotation."""
        transformer = JSToTypeScriptTransformer(temp_project)
        
        code = "function greet(name) { return `Hello, ${name}`; }"
        result = transformer._add_function_types(code)
        
        assert 'name:' in result or ': any' in result
    
    def test_arrow_function_annotation(self, temp_project):
        """Test arrow function annotation."""
        transformer = JSToTypeScriptTransformer(temp_project)
        
        code = "const greet = (name) => `Hello, ${name}`"
        result = transformer._add_function_types(code)
        
        assert 'name:' in result or ': any' in result
    
    def test_primitive_type_inference(self, temp_project):
        """Test type inference for primitives."""
        transformer = JSToTypeScriptTransformer(temp_project)
        
        code = "const count = 5"
        result = transformer._add_variable_types(code)
        
        assert ': number' in result
    
    def test_string_type_inference(self, temp_project):
        """Test string type inference."""
        transformer = JSToTypeScriptTransformer(temp_project)
        
        code = 'const name = "Alice"'
        result = transformer._add_variable_types(code)
        
        assert ': string' in result


class TestTransformerIntegration:
    """Integration tests for transformers."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_react_component_full_transformation(self, temp_project):
        """Test full React component transformation."""
        project_path = Path(temp_project)
        
        # Create test file
        test_file = project_path / "Counter.jsx"
        test_file.write_text(TEST_FIXTURES['react_component']['content'])
        
        # Transform
        transformer = ReactToVueTransformer(temp_project)
        results = transformer.transform_files(["Counter.jsx"])
        
        assert len(results) == 1
        assert results[0].confidence > 0.7
        assert results[0].changes_count > 0
    
    def test_python_file_full_transformation(self, temp_project):
        """Test full Python file transformation."""
        project_path = Path(temp_project)
        
        # Create test file
        test_file = project_path / "legacy.py"
        test_file.write_text(TEST_FIXTURES['python2_code']['content'])
        
        # Transform
        transformer = PythonTransformer(temp_project)
        results = transformer.transform_files(["legacy.py"])
        
        assert len(results) == 1
        assert results[0].confidence > 0.7
        assert 'print(' in results[0].after


@pytest.mark.performance
class TestTransformerPerformance:
    """Performance tests for transformers."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_large_file_transformation(self, temp_project):
        """Test transformation of large files."""
        project_path = Path(temp_project)
        
        # Create a large Python file
        large_content = TEST_FIXTURES['python2_code']['content'] * 100
        test_file = project_path / "large.py"
        test_file.write_text(large_content)
        
        # Transform and measure time
        import time
        transformer = PythonTransformer(temp_project)
        
        start = time.time()
        results = transformer.transform_files(["large.py"])
        duration = time.time() - start
        
        # Should complete within reasonable time
        assert duration < 10  # 10 seconds max
        assert len(results) == 1


class TestReactToAngularTransformer:
    """Test React to Angular transformations."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_detect_react_component(self, temp_project):
        """Test React component detection."""
        from apps.backend.migration.transformers.react_to_angular import ReactToAngularTransformer
        
        transformer = ReactToAngularTransformer(temp_project)
        
        react_code = TEST_FIXTURES['react_component']['content']
        assert transformer._is_react_component(react_code)
        
        # Non-React code
        assert not transformer._is_react_component("const x = 5")
    
    def test_convert_props_to_inputs(self, temp_project):
        """Test props to @Input conversion."""
        from apps.backend.migration.transformers.react_to_angular import ReactToAngularTransformer
        
        transformer = ReactToAngularTransformer(temp_project)
        
        code = "function Counter({ count, onIncrement }) { return <div>{count}</div> }"
        result = transformer._transform_props_to_inputs(code)
        
        assert '@Input()' in result
        assert 'count' in result
        assert 'onIncrement' in result
    
    def test_transform_state_to_properties(self, temp_project):
        """Test state to properties conversion."""
        from apps.backend.migration.transformers.react_to_angular import ReactToAngularTransformer
        
        transformer = ReactToAngularTransformer(temp_project)
        
        code = "const [count, setCount] = useState(0)"
        result = transformer._transform_state_to_properties(code)
        
        assert 'count: any = 0' in result
        assert 'useState' not in result
    
    def test_transform_hooks_to_lifecycle(self, temp_project):
        """Test hooks to lifecycle conversion."""
        from apps.backend.migration.transformers.react_to_angular import ReactToAngularTransformer
        
        transformer = ReactToAngularTransformer(temp_project)
        
        code = "useEffect(() => { console.log('init') }, [])"
        result = transformer._transform_hooks_to_lifecycle(code)
        
        assert 'ngOnInit()' in result
        assert 'useEffect' not in result
    
    def test_full_react_to_angular_transformation(self, temp_project):
        """Test full React to Angular transformation."""
        from apps.backend.migration.transformers.react_to_angular import ReactToAngularTransformer
        from pathlib import Path
        
        project_path = Path(temp_project)
        
        # Create test file
        test_file = project_path / "Counter.jsx"
        test_file.write_text(TEST_FIXTURES['react_component']['content'])
        
        # Transform
        transformer = ReactToAngularTransformer(temp_project)
        results = transformer.transform_files(["Counter.jsx"])
        
        assert len(results) == 1
        assert results[0].confidence > 0.7
        assert '@Component' in results[0].after
        assert 'export class' in results[0].after


class TestJSToCSharpTransformer:
    """Test JavaScript to C# transformations."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_type_mappings(self, temp_project):
        """Test type system conversions."""
        from apps.backend.migration.transformers.js_to_csharp import JSToCSharpTransformer
        
        transformer = JSToCSharpTransformer(temp_project)
        
        assert transformer.TYPE_MAPPINGS['string'] == 'string'
        assert transformer.TYPE_MAPPINGS['number'] == 'double'
        assert transformer.TYPE_MAPPINGS['boolean'] == 'bool'
        assert transformer.TYPE_MAPPINGS['any'] == 'dynamic'
    
    def test_transform_imports_to_using(self, temp_project):
        """Test import to using statement conversion."""
        from apps.backend.migration.transformers.js_to_csharp import JSToCSharpTransformer
        
        transformer = JSToCSharpTransformer(temp_project)
        
        code = "import { Component } from '@angular/core'"
        result = transformer._transform_imports(code)
        
        assert 'using' in result
        assert 'import' not in result
    
    def test_transform_variables(self, temp_project):
        """Test variable declaration conversion."""
        from apps.backend.migration.transformers.js_to_csharp import JSToCSharpTransformer
        
        transformer = JSToCSharpTransformer(temp_project)
        
        code = "const name: string = 'John'"
        result = transformer._transform_variables(code)
        
        assert 'string name =' in result
        assert 'const' not in result
    
    def test_transform_template_literals(self, temp_project):
        """Test template literal conversion."""
        from apps.backend.migration.transformers.js_to_csharp import JSToCSharpTransformer
        
        transformer = JSToCSharpTransformer(temp_project)
        
        code = "`Hello, ${name}!`"
        result = transformer._transform_template_literals(code)
        
        assert '$"' in result
        assert '${' not in result
    
    def test_transform_array_methods(self, temp_project):
        """Test array method conversion."""
        from apps.backend.migration.transformers.js_to_csharp import JSToCSharpTransformer
        
        transformer = JSToCSharpTransformer(temp_project)
        
        code = "items.map(x => x.id).filter(id => id > 0)"
        result = transformer._transform_arrays(code)
        
        assert '.Select(' in result
        assert '.Where(' in result
        assert '.map(' not in result
        assert '.filter(' not in result
    
    def test_transform_string_methods(self, temp_project):
        """Test string method conversion."""
        from apps.backend.migration.transformers.js_to_csharp import JSToCSharpTransformer
        
        transformer = JSToCSharpTransformer(temp_project)
        
        code = "name.toUpperCase().trim()"
        result = transformer._transform_strings(code)
        
        assert '.ToUpper(' in result
        assert '.Trim(' in result
        assert '.toUpperCase' not in result
    
    def test_full_js_to_csharp_transformation(self, temp_project):
        """Test full JavaScript to C# transformation."""
        from apps.backend.migration.transformers.js_to_csharp import JSToCSharpTransformer
        from pathlib import Path
        
        project_path = Path(temp_project)
        
        # Create test file
        test_file = project_path / "service.js"
        test_file.write_text("const getData = async (id) => { return await fetch(`/api/${id}`); }")
        
        # Transform
        transformer = JSToCSharpTransformer(temp_project)
        results = transformer.transform_files(["service.js"])
        
        assert len(results) == 1
        assert results[0].file_path.endswith('.cs')
        assert 'namespace' in results[0].after
        assert 'async Task' in results[0].after


class TestIntegrationNewTransformers:
    """Integration tests for new transformers."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_react_to_angular_full_pipeline(self, temp_project):
        """Test full React to Angular pipeline."""
        from apps.backend.migration.transformer import TransformationEngine
        from pathlib import Path
        
        project_path = Path(temp_project)
        
        # Create test component
        test_file = project_path / "Button.jsx"
        test_file.write_text("""
import React, { useState } from 'react'

function Button({ label, onClick }) {
  const [clicked, setClicked] = useState(false)
  
  return <button onClick={() => setClicked(true)}>{label}</button>
}

export default Button
""")
        
        # Transform
        engine = TransformationEngine(temp_project, "react", "angular")
        results = engine.transform_code()
        
        assert len(results) > 0
        assert results[0].confidence > 0.7
    
    def test_js_to_csharp_full_pipeline(self, temp_project):
        """Test full JavaScript to C# pipeline."""
        from apps.backend.migration.transformer import TransformationEngine
        from pathlib import Path
        
        project_path = Path(temp_project)
        
        # Create test file
        test_file = project_path / "utils.js"
        test_file.write_text("""
const formatName = (firstName, lastName) => {
  return `${firstName.toUpperCase()} ${lastName.toUpperCase()}`
}

const filterActive = (items) => {
  return items.filter(x => x.active).map(x => x.name)
}
""")
        
        # Transform
        engine = TransformationEngine(temp_project, "javascript", "csharp")
        results = engine.transform_code()
        
        assert len(results) > 0
        assert any(r.file_path.endswith('.cs') for r in results)


class TestNewTransformerErrors:
    """Test error handling in new transformers."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_react_to_angular_missing_file(self, temp_project):
        """Test handling of missing files."""
        from apps.backend.migration.transformers.react_to_angular import ReactToAngularTransformer
        
        transformer = ReactToAngularTransformer(temp_project)
        results = transformer.transform_files(["nonexistent.jsx"])
        
        # Should not crash, just return empty or error result
        assert isinstance(results, list)
    
    def test_js_to_csharp_invalid_syntax(self, temp_project):
        """Test handling of invalid JavaScript."""
        from apps.backend.migration.transformers.js_to_csharp import JSToCSharpTransformer
        from pathlib import Path
        
        project_path = Path(temp_project)
        test_file = project_path / "broken.js"
        test_file.write_text("function test() {{{{{")  # Invalid syntax
        
        transformer = JSToCSharpTransformer(temp_project)
        results = transformer.transform_files(["broken.js"])
        
        # Should handle gracefully
        assert isinstance(results, list)
        if results:
            assert results[0].confidence >= 0 or results[0].errors