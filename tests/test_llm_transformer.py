"""
Unit tests for LLM Transformer
Tests LLM-enhanced code transformation functionality
"""

import pytest
from pathlib import Path
import tempfile
import os

from apps.backend.migration.llm_transformer import LLMTransformer
from apps.backend.migration.models import TransformationResult


@pytest.fixture
def temp_project():
    """Create temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_transformation():
    """Sample transformation result."""
    return TransformationResult(
        file_path="test.jsx",
        transformation_type="jsx_to_vue",
        before="""
import React, { useState } from 'react';

export default function Counter() {
  const [count, setCount] = useState(0);
  
  return (
    <div className="counter">
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
    </div>
  );
}
""",
        after="""
<template>
  <div class="counter">
    <p>Count: {{ count }}</p>
    <button @click="count++">Increment</button>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const count = ref(0);
</script>
""",
        changes_count=5,
        confidence=0.75,
        validation_passed=False,
    )


class TestLLMTransformer:
    """Test LLM Transformer functionality."""
    
    def test_initialization(self, temp_project):
        """Test LLM transformer initialization."""
        transformer = LLMTransformer(temp_project)
        
        assert transformer.project_dir == Path(temp_project)
        assert transformer.api_key == os.getenv("ANTHROPIC_API_KEY")
    
    def test_initialization_with_api_key(self, temp_project):
        """Test initialization with explicit API key."""
        transformer = LLMTransformer(temp_project, api_key="test-key")
        
        assert transformer.api_key == "test-key"
        assert transformer.client is not None
    
    def test_build_prompt(self, temp_project, sample_transformation):
        """Test prompt building."""
        transformer = LLMTransformer(temp_project)
        
        prompt = transformer._build_prompt(
            sample_transformation.before,
            sample_transformation.after,
            "react",
            "vue",
            "react_to_vue.md",
        )
        
        assert "react" in prompt.lower()
        assert "vue" in prompt.lower()
        assert "useState" in prompt  # Original code
        assert "ref" in prompt  # Transformed code
    
    def test_generic_prompt_fallback(self, temp_project, sample_transformation):
        """Test generic prompt fallback."""
        transformer = LLMTransformer(temp_project)
        
        prompt = transformer._build_prompt(
            sample_transformation.before,
            sample_transformation.after,
            "react",
            "vue",
            "nonexistent_template.md",  # This file doesn't exist
        )
        
        # Should still generate a valid prompt
        assert len(prompt) > 100
        assert "react" in prompt.lower()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No API key")
    async def test_enhance_transformation(self, temp_project, sample_transformation):
        """Test LLM enhancement of transformation."""
        transformer = LLMTransformer(temp_project)
        
        enhanced = await transformer.enhance_transformation(
            sample_transformation,
            "react",
            "vue",
            "react_to_vue.md",
        )
        
        # Should improve confidence
        assert enhanced.confidence >= sample_transformation.confidence
        
        # Should mark as LLM enhanced
        assert hasattr(enhanced, 'llm_enhanced')
        assert enhanced.llm_enhanced is True
        
        # Should have enhanced code
        assert len(enhanced.after) > 0
        assert enhanced.after != sample_transformation.after  # Should be different
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No API key")
    async def test_enhance_transformations_batch(self, temp_project):
        """Test batch enhancement of multiple transformations."""
        transformer = LLMTransformer(temp_project)
        
        # Create multiple transformations
        transformations = [
            TransformationResult(
                file_path=f"test{i}.jsx",
                transformation_type="jsx_to_vue",
                before=f"const Component{i} = () => <div>Test {i}</div>;",
                after=f"<template><div>Test {i}</div></template>",
                changes_count=1,
                confidence=0.7,
                validation_passed=False,
            )
            for i in range(3)
        ]
        
        enhanced = await transformer.enhance_transformations_batch(
            transformations,
            "react",
            "vue",
            "react_to_vue.md",
            max_concurrent=2,
        )
        
        # Should enhance all
        assert len(enhanced) == 3
        
        # All should be marked as enhanced
        assert all(hasattr(e, 'llm_enhanced') and e.llm_enhanced for e in enhanced)
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No API key")
    async def test_validate_transformation(self, temp_project, sample_transformation):
        """Test LLM validation of transformation."""
        transformer = LLMTransformer(temp_project)
        
        is_valid = await transformer.validate_transformation(sample_transformation)
        
        # Should return boolean
        assert isinstance(is_valid, bool)
        
        # Should update validation status
        assert hasattr(sample_transformation, 'validation_passed')
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No API key")
    async def test_suggest_manual_changes(self, temp_project, sample_transformation):
        """Test LLM suggestions for manual review."""
        transformer = LLMTransformer(temp_project)
        
        suggestions = await transformer.suggest_manual_changes(sample_transformation)
        
        # Should return list
        assert isinstance(suggestions, list)
        
        # If suggestions exist, should have proper structure
        if suggestions:
            for suggestion in suggestions:
                assert 'line_number' in suggestion or 'description' in suggestion
    
    @pytest.mark.asyncio
    async def test_enhance_without_api_key(self, temp_project, sample_transformation):
        """Test enhancement fails gracefully without API key."""
        # Create transformer without API key
        transformer = LLMTransformer(temp_project, api_key=None)
        transformer.client = None
        
        enhanced = await transformer.enhance_transformation(
            sample_transformation,
            "react",
            "vue",
            "react_to_vue.md",
        )
        
        # Should return original without changes
        assert enhanced == sample_transformation
        assert not hasattr(enhanced, 'llm_enhanced') or not enhanced.llm_enhanced
    
    @pytest.mark.asyncio
    async def test_error_handling(self, temp_project):
        """Test error handling in LLM enhancement."""
        transformer = LLMTransformer(temp_project, api_key="invalid-key")
        
        bad_result = TransformationResult(
            file_path="test.jsx",
            transformation_type="jsx_to_vue",
            before="invalid code",
            after="also invalid",
            changes_count=0,
            confidence=0.1,
            validation_passed=False,
        )
        
        enhanced = await transformer.enhance_transformation(
            bad_result,
            "react",
            "vue",
            "react_to_vue.md",
        )
        
        # Should add error to result
        assert len(enhanced.errors) > 0
        assert any("error" in e.lower() for e in enhanced.errors)
    
    def test_get_generic_prompt(self, temp_project):
        """Test generic prompt generation."""
        transformer = LLMTransformer(temp_project)
        
        prompt = transformer._get_generic_prompt()
        
        assert len(prompt) > 50
        assert "code" in prompt.lower()
        assert "transformation" in prompt.lower() or "migration" in prompt.lower()


class TestLLMTransformerIntegration:
    """Integration tests for LLM transformer."""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No API key")
    async def test_full_enhancement_workflow(self, temp_project):
        """Test complete enhancement workflow."""
        from apps.backend.migration.transformer import TransformationEngine
        
        # Create test project
        project_path = Path(temp_project)
        src_dir = project_path / "src"
        src_dir.mkdir()
        
        test_file = src_dir / "Component.jsx"
        test_file.write_text("""
import React, { useState } from 'react';

export default function Component() {
  const [value, setValue] = useState('');
  
  return (
    <div>
      <input value={value} onChange={(e) => setValue(e.target.value)} />
      <p>You typed: {value}</p>
    </div>
  );
}
""")
        
        # Run base transformation
        transformer = TransformationEngine(temp_project, "react", "vue")
        results = transformer.transform_code()
        
        assert len(results) > 0
        
        # Enhance with LLM
        llm_transformer = LLMTransformer(temp_project)
        enhanced = await llm_transformer.enhance_transformations_batch(
            results,
            "react",
            "vue",
            "react_to_vue.md",
        )
        
        # Should have improved results
        assert len(enhanced) == len(results)
        
        # Confidence should be same or better
        for original, enhanced_result in zip(results, enhanced):
            assert enhanced_result.confidence >= original.confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
