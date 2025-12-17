"""
Delete operation result model.
"""

class DeleteResult:
    """Result of a delete operation."""
    
    def __init__(self, success: bool, already_deleted: bool = False):
        """
        Initialize delete result.
        
        Args:
            success: True if the delete operation was successful
            already_deleted: True if the article was already deleted (404/not found)
        """
        self.success = success
        self.already_deleted = already_deleted
    
    def __bool__(self):
        """For backward compatibility, return True if successful or already deleted."""
        return self.success or self.already_deleted
    
    def __repr__(self):
        if self.success:
            return "DeleteResult(success=True)"
        elif self.already_deleted:
            return "DeleteResult(already_deleted=True)"
        else:
            return "DeleteResult(failed=True)"