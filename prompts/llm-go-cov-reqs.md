# Go Code Coverage Analysis Instructions

## Purpose
To analyze Go code coverage data and identify areas that need additional unit tests, helping developers improve test coverage by highlighting uncovered code sections and suggesting appropriate test strategies.

## Required Input
1. Path to Go source code repository
2. Optional coverage threshold percentage (default: analyze all files with any uncovered code)

## Execution Steps

### 1. Generate Coverage Data
1. Navigate to the Go project directory
2. Run tests with coverage enabled: `go test ./... -coverprofile=coverage.out`
3. Verify coverage file was created successfully

### 2. Parse Coverage File
1. Extract uncovered code sections from the coverage file
2. Identify files with coverage below threshold (if specified)
3. Merge adjacent or overlapping uncovered sections for clearer analysis
4. Skip files with coverage percentage above threshold (if specified)

### 3. Analyze Each Uncovered File
1. Read the source code file
2. Calculate coverage statistics (total lines, uncovered lines, coverage percentage)
3. Identify specific uncovered code sections with line numbers
4. Examine each uncovered section to understand its functionality
5. Determine what types of tests would be most appropriate

### 4. Generate Test Recommendations
1. For each uncovered section, identify:
   - Function purpose and expected behavior
   - Input parameters and return values
   - Edge cases and error conditions
   - Dependencies that might need mocking
2. Suggest specific test cases with example code
3. Recommend appropriate testing techniques (table-driven tests, mocks, etc.)

## Output Format
For each input file with insufficient coverage create a file with the name "<original_file_name>.cov.md" with the next information:
1. **File Header**
   ```
   ==========================================================================
   File: [relative_path_to_file]
   Coverage: [percentage]% ([uncovered_lines] uncovered lines, [sections] sections)
   ==========================================================================
   ```

2. **For Each Uncovered Section**
   ```
   --------------------------------------------------------------------------
   SECTION [section_number]: Lines [start_line]-[end_line]
   // >>> GENERATE MORE UNIT TESTS FOR THIS SECTION:
   [code_snippet]
   // <<< END OF SECTION
   
   TEST RECOMMENDATIONS:
   [specific_test_cases_and_examples]
   ```

## Example Output

```
==========================================================================
File: internal/service/user.go
Coverage: 75.50% (50 uncovered lines, 3 sections)
==========================================================================

--------------------------------------------------------------------------
SECTION 1: Lines 45-60
// >>> GENERATE MORE UNIT TESTS FOR THIS SECTION:
func (s *Service) GetUser(id string) (*User, error) {
    if id == "" {
        return nil, errors.New("empty user ID")
    }
    
    user, err := s.repo.FindByID(id)
    if err != nil {
        return nil, fmt.Errorf("failed to get user: %w", err)
    }
    
    if user == nil {
        return nil, ErrUserNotFound
    }
    
    return user, nil
}
// <<< END OF SECTION

TEST RECOMMENDATIONS:
1. Test with empty ID parameter (should return error)
2. Test when repository returns error (should propagate error)
3. Test when user is not found (should return ErrUserNotFound)
4. Test successful retrieval (should return user)

Example test code:
```go
func TestService_GetUser(t *testing.T) {
    tests := []struct {
        name    string
        id      string
        mockFn  func(r *mockRepo)
        want    *User
        wantErr error
    }{
        // Test cases here
    }
    // Test implementation
}
```
```

## Testing Guidelines

1. **Coverage Priority**
   - Focus on error handling paths first
   - Test boundary conditions and edge cases
   - Ensure all logical branches are covered

2. **Testing Techniques**
   - Use table-driven tests for functions with multiple scenarios
   - Create mock implementations for external dependencies
   - Use subtests for better organization and readability
   - Consider using testify or other testing libraries for assertions

3. **Implementation Tips**
   - Write tests for one uncovered section at a time
   - Run coverage analysis after adding each test to verify improvement
   - Consider refactoring complex functions to make them more testable

## Common Testing Patterns

1. **For HTTP Handlers**
   - Test with various request methods, paths, and body content
   - Test with missing or invalid headers/parameters
   - Verify correct status codes and response bodies

2. **For Database Operations**
   - Test with mock database implementations
   - Test error conditions (connection failures, constraint violations)
   - Test with various query parameters

3. **For Business Logic**
   - Test all conditional branches
   - Test with valid and invalid inputs
   - Test edge cases and boundary conditions
